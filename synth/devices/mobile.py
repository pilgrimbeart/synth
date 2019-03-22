"""
mobile
=======
Devices which move in a predictable way

Configurable parameters::

    {
        "area_centre" : e.g. "London, UK"       } optional, but both must be specified if either are. Points-to-visit will be within this set.
        "area_radius" : e.g. "Manchester, UK"   } 
        "points_to_visit" : 4   number of points to visit. Optional, but if specified then must be at least 2
        "google_maps_key" : "xyz" } Google Maps now requires this. Often defined in ../synth_accounts/default.json
    }

Device properties created::

    {
        "latitude" : latitude in degrees as a floating-point number
        "longitude" : longitude in degrees as a floating-point number
    }
"""

from device import Device
from helpers.geo import google_maps, geo
import random


# We gradually move from point to point, and dwell for a while at each point
UPDATE_PERIOD_S = 60*60 # Once an hour
DWELL_MIN = 3   # In units of UPDATE_PERIOD_S
DWELL_MAX = 24 * 14 # Units can dwell for up to a fortnight
TRAVEL_RATE_MIN = 1.0/12  # What fraction of the distance between two points is travelled in every update period?
TRAVEL_RATE_MAX = 1.0/3
SEND_AT_LEAST_EVERY = 99999999999   # Even when not moving, send an update at least this often (large number for never)

NUMBER_OF_LOCATIONS = 10

class Mobile(Device):
    # Class variables
    pp = None
    
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Mobile,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.generate_addresses = params["mobile"].get("generate_addresses", False)
        self.area_centre = params["mobile"].get("area_centre", None)
        self.area_radius = params["mobile"].get("area_radius", None)
        self.points_to_visit =params["mobile"].get("points_to_visit", 4)

        if (Mobile.pp is None):  # Only load map at start, as very expensive operation
            Mobile.pp = geo.point_picker()  # Very expensive, so do only once
            area = None
            if self.area_centre != None:
                area = [self.area_centre, self.area_radius]
            google_maps_key = context.get("google_maps_key", None)
            Mobile.locations = []   # Array of (lon,lat,address)
            for L in range(NUMBER_OF_LOCATIONS):
                (lon,lat) = Mobile.pp.pick_point(area, google_maps_key)
                address_info = google_maps.lon_lat_to_address(lon, lat, google_maps_key)
                Mobile.locations.append( (lon,lat, address_info["address_postal_town"]) )
            Mobile.base_location = random.randrange(0, NUMBER_OF_LOCATIONS)

        self.points = []    # Array of indices into Mobile.locations[]
        self.points.append(Mobile.base_location)   # All pallets start at the base location
        for P in range(self.points_to_visit-1):
            while True:
                loc = random.randrange(0, NUMBER_OF_LOCATIONS)
                if loc not in self.points:
                    break   # Ensure no repeats (which means we'll hang if we try to choose more points than locations!)
            self.points.append(loc)

        self.from_point = 0
        self.to_point = 1
        self.travel_fraction = 0.0
        self.travel_rate = TRAVEL_RATE_MIN + random.random() * (TRAVEL_RATE_MAX-TRAVEL_RATE_MIN)
        self.dwell_count = random.randrange(DWELL_MIN, DWELL_MAX)   # While dwell_count > 0, device stays still
        self.update_everything()

        self.engine.register_event_in(UPDATE_PERIOD_S, self.tick_update_position, self, self)

    def comms_ok(self):
        return super(Mobile,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Mobile,self).external_event(event_name, arg)

    def close(self):
        super(Mobile,self).close()

    # Private methods

    def update_lon_lat(self):
        lon_from = Mobile.locations[self.points[self.from_point]][0]
        lon_to =   Mobile.locations[self.points[self.to_point]][0]
        lat_from = Mobile.locations[self.points[self.from_point]][1]
        lat_to =   Mobile.locations[self.points[self.to_point]][1]
        lon = lon_from * (1.0 - self.travel_fraction) + lon_to * self.travel_fraction
        lat = lat_from * (1.0 - self.travel_fraction) + lat_to * self.travel_fraction
        self.set_property("longitude", lon)
        self.set_property("latitude", lat)

    def update_moving_and_location(self):
        self.set_property("moving", self.dwell_count == 0)
        if self.dwell_count == 0:
            self.set_property("location", None)
        else:
            self.set_property("location", Mobile.locations[self.points[self.from_point]][2])

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
            if self.travel_fraction > 1.0: # Reached destination
                self.from_point = (self.from_point + 1) % self.points_to_visit
                self.to_point = (self.to_point + 1) % self.points_to_visit
                self.travel_fraction = 0.0
                self.travel_rate = TRAVEL_RATE_MIN + random.random() * (TRAVEL_RATE_MAX-TRAVEL_RATE_MIN)
                self.dwell_count = random.randrange(DWELL_MIN, DWELL_MAX)
                self.update_everything()
            else:
                self.update_lon_lat()
        self.engine.register_event_in(UPDATE_PERIOD_S, self.tick_update_position, self, self)
