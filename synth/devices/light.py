"""
light
=====
Simulates a light sensors, given a device which has a longitude and latitude.
Reacts appropriately to location on Earth, time-of-day and season-of-year.

Arguments::

    {
    }

Properties::

    light : updates once an hour with the local light level
"""

from device import Device
from helpers.solar import solar
import random

class Light(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        super(Light,self).__init__(instance_name, time, engine, update_callback, params)
        engine.register_event_in(0, self.tick_light, self)

    def comms_ok(self):
        return super(Light,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Light,self).external_event(event_name, arg)
        pass

    def close(self, err_str):
        super(Light,self).close(err_str)

    # Private methods
    def tick_light(self, _):
        lon = float(self.properties.get("longitude", 0.0))
        lat = float(self.properties.get("latitude", 0.0))
        light = solar.sun_bright(self.engine.get_now(), lon, lat)
        self.set_property("light", light)
        self.engine.register_event_in(60*60, self.tick_light, self)
