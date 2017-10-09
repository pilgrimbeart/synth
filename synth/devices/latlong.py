"""
latlong
=======
Scatters devices on the surface of the Earth in a realistic way according to population.
If no arguments are provided, devices are scattered across the whole Earth.
Uses a Google Maps API.

Configurable parameters::

    {
        "area_centre" : e.g. "London, UK"       } optional, but both must be specified if either are
        "area_radius" : e.g. "Manchester, UK"   } 
        "map_file" : e.g. "devicepilot_logo" - optional
        "google_maps_key" : "xyz" } optional. Often defined in ..\synth_accounts\default
    }

Device properties created::

    {
        "latitude" : latitude in degrees as a floating-point number
        "longitude" : longitude in degrees as a floating-point number
    }
"""

from device import Device
from helpers.geo import geo

class Latlong(Device):
    # Class variables
    map_file = None
    pp = None
    
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Latlong,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.area_centre = params["latlong"].get("area_centre", None)
        self.area_radius = params["latlong"].get("area_radius", None)
        self.map_file = params["latlong"].get("map_file", None)
        if (Latlong.pp is None) or (Latlong.map_file != self.map_file):  # Only load map at start, or if changed, as very expensive operation
            Latlong.pp = geo.point_picker(self.map_file)  # Very expensive, so do only once
            Latlong.map_file = self.map_file

        area = None
        if self.area_centre != None:
            area = [self.area_centre, self.area_radius]
        google_maps_key = context.get("google_maps_key", None)
        (lon,lat) = Latlong.pp.pick_point(area, google_maps_key)
        self.set_properties( { 'latitude' : lat, 'longitude' : lon } )

    def comms_ok(self):
        return super(Latlong,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Latlong,self).external_event(event_name, arg)

    def close(self):
        super(Latlong,self).close()

