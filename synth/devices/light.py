"""
light
=====
Simulates a light sensor, given a device which has a longitude and latitude.
Reacts appropriately to location on Earth, time-of-day and season-of-year.

Configurable parameters::

    {
    }

Device properties created::

    {
        "light" : updates once an hour with the local light level
        "clouds" : true (optional)
        "generate" : true (optional) - create "power" and "energy" properties for solar PV (-ve because generating)
    }

"""

from .device import Device
from helpers.solar import solar
import math, random

TICK_INTERVAL_S = 60*60

DEFAULT_GEN_SCALAR = -0.5

class Light(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Light,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.use_clouds = params["light"].get("clouds", False)
        self.generate = params["light"].get("generate", False)
        if self.generate:
            scalar = float(params["light"].get("generate_scalar", DEFAULT_GEN_SCALAR))
            r = random.normalvariate(scalar, scalar/10.0)
            self.gen_light_to_power_ratio = max(scalar * 0.7, min(scalar * 1.3, r))
            self.set_property("energy", 0.0)
        engine.register_event_in(0, self.tick_light, self, self)

    def comms_ok(self):
        return super(Light,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Light,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Light,self).close()

    # Private methods
    def tick_light(self, _):
        lon = float(self.properties.get("longitude", 0.0))
        lat = float(self.properties.get("latitude", 0.0))
        light = solar.sun_bright(self.engine.get_now(), lon, lat)
        if self.use_clouds:
            t = self.engine.get_now() + hash(self.get_property("longitude",0)+self.get_property("latitude",0))   # Unique per location
            hours = self.engine.get_now()/(60*60)
            days = self.engine.get_now()/(60*60*24)
            months = self.engine.get_now()/(60*60*24*30)
            cloud_effect = 0.5 + (
                    math.sin(hours) + math.sin(hours*1.3) + math.sin(hours*1.7) + math.sin(hours*1.9) +
                    math.sin(days * 1.3) + math.sin(days * 1.7) + math.sin(days * 1.9) +
                    math.sin(months * 1.3) + math.sin(months*1.7) + math.sin(months * 7)) / (10 * 2.0)
            light *= cloud_effect

        p = { "light" : light }
        if self.generate:
            pow = light * self.gen_light_to_power_ratio
            p.update( {
                "power" : pow,
                "energy" : self.get_property("energy") + pow * TICK_INTERVAL_S/(60*60.0)
                })
            self.set_properties(p)
        self.engine.register_event_in(TICK_INTERVAL_S, self.tick_light, self, self)
