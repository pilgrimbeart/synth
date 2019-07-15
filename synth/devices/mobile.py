"""
mobile
=======
Devices which move in a predictable way

Configurable parameters::

    {
        "area_centre" : e.g. "London, UK"       } optional, but both must be specified if either are. Points-to-visit will be within this set.
        "area_radius" : e.g. "Manchester, UK"   } 
        "points_to_visit" : 4   number of points to visit. Optional, but if specified then must be at least 2
        "generate_fleet_management_metrics" : False      If true then output several properties to do with fleet management (fuel, miles etc.)
        "google_maps_key" : "xyz" } Google Maps now requires this. Often defined in ../synth_accounts/default.json
    }

Device properties created::

    {
        "latitude" : latitude in degrees as a floating-point number
        "longitude" : longitude in degrees as a floating-point number
    }
"""

from device import Device
from common.geo import google_maps, geo
import random, math
import logging


# Because we need to cache the geo point-picker, we have two levels of hierarchy:
# 1) Mobile behaviour may be instantiated by entirely different, unconnected groups of devices - for example mobile pallets in England and mobile trucks in LA.
#    So we call each of these a "loc_group" and cache the (expensive) point picker and location lookups per loc_group.
# 2) All devices in that loc_group then share that defined set of locations to visit, though they each set their own unique itinerary between locations (points[])

# We gradually move from point to point, and dwell for a while at each point
UPDATE_PERIOD_S = 60*60 # Once an hour
UPDATE_PERIOD_H = UPDATE_PERIOD_S/(60*60)
MPH_MIN = 5
MPH_MAX = 70
SEND_AT_LEAST_EVERY = 99999999999   # Even when not moving, send an update at least this often (large number for never)

NUMBER_OF_LOCATIONS = 10

MPG = 8 # USA levels of fuel-efficiency!
LATLON_TO_MILES = 88    # Very approximate conversion factor from "latlong distance in degrees" to miles!

class Location_group():
    def __init__(self, context, area_centre, area_radius):
        self.pp = geo.point_picker()  # Very expensive, so do only once
        area = None
        if area_centre != None:
            area = [area_centre, area_radius]
        google_maps_key = context.get("google_maps_key", None)
        self.locations = []   # Array of (lon,lat,address)
        for L in range(NUMBER_OF_LOCATIONS):    # Choose locations devices will visit
            while True:
                (lon,lat) = self.pp.pick_point(area, google_maps_key)
                address_info = google_maps.lon_lat_to_address(lon, lat, google_maps_key)
                if ("address_postal_town" in address_info) or ("address_route" in address_info): # Only use locations which have addresses (e.g. don't accidentally pick the sea!)
                    break
            if "address_postal_town" in address_info:
                addr = address_info["address_postal_town"]
            else:
                addr = address_info["address_route"]
            logging.info("Location "+str(L)+" for mobile devices to visit is "+repr(addr))
            self.locations.append( (lon,lat, addr) )
        self.base_location = random.randrange(0, NUMBER_OF_LOCATIONS)
    
class Mobile(Device):
    # Class variables
    loc_groups = {}
    
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Mobile,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.generate_addresses = params["mobile"].get("generate_addresses", False)
        self.area_centre = params["mobile"].get("area_centre", None)
        self.area_radius = params["mobile"].get("area_radius", None)
        self.points_to_visit = params["mobile"].get("points_to_visit", 4)
        self.fleet_mgmt = params["mobile"].get("generate_fleet_management_metrics", False)
        self.dwell_h_min = params["mobile"].get("dwell_h_min", 3)
        self.dwell_h_max = params["mobile"].get("dwell_h_max", 24*14)
        self.tire_deflation_rate = min(1.0, 1.0 - random.gauss(0.001, 0.0001))

        the_key = str(self.area_centre) + "." + str(self.area_radius)  # Needs to be unique-enough between location groups 
        if the_key not in Mobile.loc_groups:
            Mobile.loc_groups[the_key] = Location_group(context, self.area_centre, self.area_radius)   # Creates a new group
        self.loc_group = Mobile.loc_groups[the_key]

        # Choose which points this device will move between
        self.points = []    # Array of indices into self.loc_group.locations[]
        self.points.append(self.loc_group.base_location)   # All pallets start at the base location
        for P in range(self.points_to_visit-1):
            while True:
                loc = random.randrange(0, NUMBER_OF_LOCATIONS)
                if loc not in self.points:
                    break   # Ensure no repeats (which means we'll hang if we try to choose more points than locations!)
            self.points.append(loc)
        
        if self.fleet_mgmt:
            self.pump_up_tires()

        self.prepare_new_journey(0,1)

        self.engine.register_event_in(UPDATE_PERIOD_S, self.tick_update_position, self, self)

    def comms_ok(self):
        return super(Mobile,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Mobile,self).external_event(event_name, arg)

    def close(self):
        super(Mobile,self).close()

    # Private methods

    def miles_between(self, lon1,lat1, lon2,lat2):
        (delta_lon, delta_lat) =  (lon2-lon1, lat2-lat1)
        return math.sqrt(delta_lon * delta_lon + delta_lat * delta_lat) * LATLON_TO_MILES

    def update_lon_lat(self):
        (prev_lon, prev_lat) = (self.get_property_or_None("longitude"), self.get_property_or_None("latitude"))
        (lon_from, lat_from) = self.loc_group.locations[self.points[self.from_point]][0:2]
        (lon_to, lat_to) = self.loc_group.locations[self.points[self.to_point]][0:2]
        lon = lon_from * (1.0 - self.travel_fraction) + lon_to * self.travel_fraction
        lat = lat_from * (1.0 - self.travel_fraction) + lat_to * self.travel_fraction
        self.set_properties({ "longitude" : lon, "latitude" : lat })    # Important to update these together (some client apps don't cope well with lat/lon being split between messages, even if contemporaneous)
        if self.fleet_mgmt:
            if prev_lon is not None:
                delta_miles = self.miles_between(prev_lon, prev_lat, lon, lat)
                self.set_property("miles", int(10*delta_miles)/10.0)
                self.set_property("av_speed_mph", int(delta_miles/UPDATE_PERIOD_H))
                self.set_property("fuel_gallons", int(100*(delta_miles/MPG))/100.0)


    def update_moving_and_location(self):
        self.set_property("moving", self.dwell_count == 0)
        if self.dwell_count == 0:
            self.set_property("location", None)
        else:
            self.set_property("location", self.loc_group.locations[self.points[self.from_point]][2])

    def update_everything(self):
        self.update_lon_lat()
        self.update_moving_and_location()

    def tick_update_position(self, _):
        if self.dwell_count > 0:    # Stationary
            if (self.dwell_count % SEND_AT_LEAST_EVERY)==0:
                self.update_lon_lat()
            self.dwell_count -= 1
            if self.dwell_count == 0:   # About to move
                self.update_everything()
        else:                       # Moving
            self.travel_fraction += self.travel_rate
            if self.travel_fraction <= 1.0:
                self.update_lon_lat()
            else:   # Reached destination
                self.prepare_new_journey((self.from_point + 1) % self.points_to_visit, (self.to_point + 1) % self.points_to_visit)
        if self.fleet_mgmt:
            tp = self.get_property("tire_pressure_psi")
            if tp < 25:
                self.pump_up_tires()    # Pump tire up again
            else:
                self.set_property("tire_pressure_psi", tp * self.tire_deflation_rate)
        self.engine.register_event_in(UPDATE_PERIOD_S, self.tick_update_position, self, self)

    def prepare_new_journey(self, from_point, to_point):
        self.from_point = from_point
        self.to_point = to_point
        self.travel_fraction = 0.0
            
        # How far to travel, and speed?
        (lon_from, lat_from) = self.loc_group.locations[self.points[self.from_point]][0:2]
        (lon_to, lat_to) = self.loc_group.locations[self.points[self.to_point]][0:2]
        miles = self.miles_between(lon_from, lat_from, lon_to, lat_to)
        mph = random.randrange(MPH_MIN, MPH_MAX)
        ticks_of_travel = (miles/mph) / UPDATE_PERIOD_H
        # therefore what fraction of entire distance to travel in each tick
        self.travel_rate = 1.0 / ticks_of_travel

        self.dwell_count = random.randrange(self.dwell_h_min/UPDATE_PERIOD_H, self.dwell_h_max/UPDATE_PERIOD_H)
        self.update_everything()

    def pump_up_tires(self):
        self.set_property("tire_pressure_psi", random.gauss(35,5))
