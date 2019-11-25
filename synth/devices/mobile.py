"""
mobile
=======
Devices which (are supposed to) move in a predictable way

Configurable parameters::

    {
        "area_centre" : e.g. "London, UK"       } optional, but both must be specified if either are. Points-to-visit will be within this set.
        "area_radius" : e.g. "Manchester, UK"   } 
        "num_locations" : 10                            The total number of defined locations 
        "points_to_visit" : 4                           Number of these locations that any individual device can visit (MUST be <= num_locations!). Optional, but if specified then must be at least 2
        "update_period" : "PT1H" (optional)             How often to update position
        "generate_fleet_management_metrics" : False     If true then output several properties to do with fleet management (fuel, miles etc.)
        "route_plan" : null (optional)                  If set then use realistic route-planning, with given mode (e.g. "walking", "driving")
        "google_maps_key" : "xyz"                       Google Maps now requires this. Often defined in ../synth_accounts/default.json
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
import isodate
import logging

MINUTES = 60
HOURS = MINUTES * 60
DAYS = HOURS * 24
WEEKS = DAYS * 7

# Because we need to cache the geo point-picker, we have two levels of hierarchy:
# 1) Mobile behaviour may be instantiated by entirely different, unconnected groups of devices - for example mobile pallets in England and mobile trucks in LA.
#    So we call each of these a "loc_group" and cache the (expensive) point picker and location lookups per loc_group.
# 2) All devices in that loc_group then share a set of potential locations they can visit
#    But each device sets its own unique fixed itinerary between some of those locations (points[])
# One reason for the above design is to minimise the combinations of routes, which would otherwise drive up our Google Maps bill by the factorial of the number of locations!

# We gradually move from point to point, and dwell for a while at each point
DEFAULT_UPDATE_PERIOD = "PT1H"
MPH_MIN = 5
MPH_MAX = 70
SEND_AT_LEAST_EVERY = 99999999999   # Even when not moving, send an update at least this often (large number for never)

DEFAULT_NUMBER_OF_LOCATIONS = 10
DEFAULT_POINTS_TO_VISIT = 4
DEFAULT_MIN_DWELL_H = 3
DEFAULT_MAX_DWELL_H = 24*14
DEFAULT_STUCK_IN_TRANSIT_MTBF = 1 * WEEKS   # amount of travel time, not elapsed time
DEFAULT_STUCK_IN_TRANSIT_RECOVERY_DURATION = 1 * WEEKS

MPG = 8 # USA levels of fuel-efficiency!
LATLON_TO_MILES = 88    # Very approximate conversion factor from "latlong distance in degrees" to miles!

class Location_group():
    """ A group of locations that devices might visit """
    def __init__(self, context, num_locs, area_centre, area_radius, first_location_at_centre=False):
        self.pp = geo.point_picker()  # Very expensive, so do only once
        area = None
        if area_centre != None:
            area = [area_centre, area_radius]
        self.google_maps_key = context.get("google_maps_key", None)
        self.locations = []   # Array of (lon,lat,address)
        for L in range(num_locs):    # Choose the locations that any devices in this loc group can visit
            first_loc = first_location_at_centre and (L==0)
            while True:
                if first_loc:
                    (lon,lat) = google_maps.address_to_lon_lat(area_centre)
                else:
                    (lon,lat) = self.pp.pick_point(area, self.google_maps_key)
                address_info = google_maps.lon_lat_to_address(lon, lat, self.google_maps_key)
                if ("address_postal_code" in address_info) and (("address_postal_town" in address_info) or ("address_route" in address_info)): # Only use locations which have addresses (e.g. don't accidentally pick the sea!)
                    break
                if first_loc:   # Avoid infinite loop if first location doesn't have required address info
                    break
            if "address_postal_town" in address_info:
                addr = address_info["address_postal_town"] + " " + address_info["address_postal_code"]
            else:
                addr = address_info["address_route"] + " " + address_info["address_postal_code"]
            logging.info("Location "+str(L)+" for mobile devices to visit is "+repr(addr)+" at "+str((lon,lat)))
            self.locations.append( (lon,lat, addr) )
        self.base_location = random.randrange(0, num_locs)
    

class Route_Follower():
    """ Understands how to follow a route made of individual segments """
    def __init__(self, route):
        self.route = route
        # logging.info("Route_Follower with route: ")
        # for r in self.route:
        #     logging.info(str(r))
        self.route_segment = 0
        self.seconds_into_segment = 0

    def current_latlon(self):
        seg = self.route[self.route_segment]
        frac = float(self.seconds_into_segment) / seg["duration"]
        # logging.info("frac="+str(frac))
        lat = seg["start_lat"] * (1.0-frac) + seg["end_lat"] * frac
        lon = seg["start_lng"] * (1.0-frac) + seg["end_lng"] * frac
        return { "latitude" : lat, "longitude" : lon }

    def time_has_passed(self, secs):
        # logging.info("time_has_passed("+str(secs)+")")
        remaining_secs = secs
        while True:
            seg = self.route[self.route_segment]
            # logging.info("route_segment="+str(self.route_segment)+" duration="+str(seg["duration"])+" seconds_into_segment="+str(self.seconds_into_segment)+" remaining_secs="+str(remaining_secs))
            if self.seconds_into_segment + remaining_secs < seg["duration"]:
                self.seconds_into_segment += remaining_secs
                break
            else:   # Move to next segment
                remaining_secs -= seg["duration"] - self.seconds_into_segment
                if self.route_segment >= len(self.route)-1: # If this was the last segment
                    self.seconds_into_segment = seg["duration"] # go to the end of it
                    break
                else:
                    self.seconds_into_segment = 0
                    self.route_segment += 1
        # logging.info("Leaving thp() with route_segment = "+str(self.route_segment)+" seconds_into_segment="+str(self.seconds_into_segment)+" remaining_secs="+str(remaining_secs))

    def journey_complete(self):
        if self.route_segment == len(self.route)-1:
            if self.seconds_into_segment >= self.route[self.route_segment]["duration"]:
                return True
        return False

    def total_journey_time(self):
        t = 0
        for seg in self.route:
            t += seg["duration"]
        return t


class Mobile(Device):
    # Class variables
    loc_groups = {}
    
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Mobile,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.generate_addresses = params["mobile"].get("generate_addresses", False)
        self.area_centre = params["mobile"].get("area_centre", None)
        self.area_radius = params["mobile"].get("area_radius", None)
        num_locs = params["mobile"].get("num_locations", DEFAULT_NUMBER_OF_LOCATIONS)
        self.points_to_visit = params["mobile"].get("points_to_visit", DEFAULT_POINTS_TO_VISIT)
        assert self.points_to_visit <= num_locs, "for mobile devices, points_to_visit must be <= num_locations"
        self.fleet_mgmt = params["mobile"].get("generate_fleet_management_metrics", False)
        self.update_period = isodate.parse_duration(params["mobile"].get("update_period", DEFAULT_UPDATE_PERIOD)).total_seconds()
        self.route_plan = params["mobile"].get("route_plan", None)
        self.dwell_h_min = params["mobile"].get("dwell_h_min", DEFAULT_MIN_DWELL_H) # "dwell" is how long an asset dwells at each target location
        self.dwell_h_max = params["mobile"].get("dwell_h_max", DEFAULT_MAX_DWELL_H)
        self.stuck_in_transit_mtbf = params["mobile"].get("stuck_in_transit_mtbf", DEFAULT_STUCK_IN_TRANSIT_MTBF)
        self.stuck_in_transit_recovery_duration = params["mobile"].get("stuck_in_transit_recovery_duration", DEFAULT_STUCK_IN_TRANSIT_RECOVERY_DURATION)
        self.stuck_in_transit = False
        self.tire_deflation_rate = min(1.0, 1.0 - random.gauss(0.001, 0.0001))
        first_location_at_centre = params["mobile"].get("first_location_at_centre", False)

        the_key = str(self.area_centre) + "." + str(self.area_radius)  # Needs to be unique-enough between location groups 
        if the_key not in Mobile.loc_groups:
            Mobile.loc_groups[the_key] = Location_group(context, num_locs, self.area_centre, self.area_radius, first_location_at_centre)   # Creates a new group
        self.loc_group = Mobile.loc_groups[the_key]

        # Choose which points this device will move between
        self.points = []    # Array of indices into self.loc_group.locations[]
        self.points.append(self.loc_group.base_location)   # All devices start at the base location
        for P in range(self.points_to_visit-1):
            while True:
                loc = random.randrange(0, len(self.loc_group.locations))
                if loc not in self.points:
                    break   # Ensure no repeats (which means we'll hang if we try to choose more points than locations!)
            self.points.append(loc)
        
        if self.fleet_mgmt:
            self.pump_up_tires()

        self.prepare_new_journey(0,1)

        self.engine.register_event_in(self.update_period, self.tick_update_position, self, self)

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
        if self.route_plan:
            self.set_properties(self.route_follower.current_latlon())
        else:   # Just driven linearly between the two points
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
                    self.set_property("av_speed_mph", int(delta_miles/(self.update_period/3600)))
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
        if self.dwell_count > 0:    # Stationary at an official Location 
            if (self.dwell_count % SEND_AT_LEAST_EVERY)==0:
                self.update_lon_lat()
            self.dwell_count -= 1
            if self.dwell_count == 0:   # About to move
                self.update_everything()
        else:                       # In transit (should be moving)
            if not self.stuck_in_transit:
                if self.stuck_in_transit_mtbf is not None:
                    if random.random() < float(self.update_period) / self.stuck_in_transit_mtbf:
                        logging.info(self.get_property("$id")+" is now stuck in transit")
                        self.stuck_in_transit = True
            else:   # IS stuck in transit
                if random.random() < float(self.update_period) / self.stuck_in_transit_recovery_duration:
                    logging.info(self.get_property("$id")+" is now unstuck and resuming transit")
                    self.stuck_in_transit = False


            if not self.stuck_in_transit:
                if self.route_plan:
                    self.route_follower.time_has_passed(self.update_period)
                    self.update_lon_lat()
                    if self.route_follower.journey_complete():
                        self.prepare_new_journey((self.from_point + 1) % self.points_to_visit, (self.to_point + 1) % self.points_to_visit)
                else:
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
        self.engine.register_event_in(self.update_period, self.tick_update_position, self, self)

    def prepare_new_journey(self, from_point, to_point):
        self.from_point = from_point
        self.to_point = to_point
        self.travel_fraction = 0.0
            
        # How far to travel, and speed?
        (lon_from, lat_from) = self.loc_group.locations[self.points[self.from_point]][0:2]
        (lon_to, lat_to) = self.loc_group.locations[self.points[self.to_point]][0:2]
        if self.route_plan:
            self.route_follower = Route_Follower(google_maps.get_route_from_lat_lons(lat_from, lon_from, lat_to, lon_to, mode=self.route_plan, google_maps_api_key = self.loc_group.google_maps_key))
            logging.info("Journey prepared for " + str(self.get_property("$id")) +
                            " from " + self.loc_group.locations[self.points[self.from_point]][2] +
                            " to " + self.loc_group.locations[self.points[self.to_point]][2] +
                            " with total journey time " + str(self.route_follower.total_journey_time()))
        else:
            miles = self.miles_between(lon_from, lat_from, lon_to, lat_to)
            mph = random.randrange(MPH_MIN, MPH_MAX)
            ticks_of_travel = (miles / mph) / (self.update_period / 3600.0) # If we try to move from a point to itself, this will be zero
            # therefore what fraction of entire distance to travel in each tick
            if ticks_of_travel == 0:
                self.travel_rate = 0
            else:
                self.travel_rate = 1.0 / ticks_of_travel

        self.dwell_count = random.randrange(self.dwell_h_min / (self.update_period / 3600.0), self.dwell_h_max / (self.update_period / 3600.0)) # Wait here for a while before commencing
        self.update_everything()

    def pump_up_tires(self):
        self.set_property("tire_pressure_psi", random.gauss(35,5))
