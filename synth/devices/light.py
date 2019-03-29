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

from device import Device
from helpers.solar import solar
import math, random

FULL_POWER = 0.5

class Light(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Light,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.use_clouds = params["light"].get("clouds", False)
        self.generate = params["light"].get("generate", False)
        if self.generate:
            self.gen_light_to_power_ratio = max(FULL_POWER * 0.7, min(FULL_POWER * 1.3, random.normalvariate(FULL_POWER, FULL_POWER/10)))
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

        self.set_property("light", light, always_send = False)
        if self.generate:
            p = light * -self.gen_light_to_power_ratio
            self.set_property("power", p, always_send = False)
            self.set_property("energy", self.get_property("energy") + p, always_send = False)
        self.engine.register_event_in(60*60, self.tick_light, self, self)
