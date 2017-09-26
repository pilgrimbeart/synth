"""
latlong
=======
Scatters devices on the surface of the Earth in a realistic way according to population.
If no arguments are provided, devices are scattered across the whole Earth.
Uses a Google Maps API.

Arguments::

    {
        "area_centre" : e.g. "London, UK"
        "area_radius" : e.g. "Manchester, UK"
    }

Properties::

    latitude : latitude in degrees as a floating-point number
    longitude : longitude in degrees as a floating-point number
"""

from device import Device
from helpers.geo import geo

pp = geo.point_picker()  # Very expensive, so do only once

class Latlong(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        super(Latlong,self).__init__(instance_name, time, engine, update_callback, params)
        self.area_centre = params["latlong"].get("area_centre", None)
        self.area_radius = params["latlong"].get("area_radius", None)
        area = None
        if self.area_centre != None:
            area = [self.area_centre, self.area_radius]
        (lon,lat) = pp.pick_point(area)
        self.set_properties( { 'latitude' : lat, 'longitude' : lon } )

    def comms_ok(self):
        return super(Latlong,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Latlong,self).external_event(event_name, arg)

    def close(self, err_str):
        super(Latlong,self).close(err_str)

