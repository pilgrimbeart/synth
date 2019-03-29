"""
bulb
=====
Simulates a light switch, given a device which has a longitude and latitude (therefore a time of day and therefore an external light level)
Reacts appropriately to location on Earth, time-of-day and season-of-year.

Configurable parameters::

    {
        "power" : (optional)    number (or list to pick from) for Watts consumed by light when on
                                if this is provided, then emits a "power" property
    }

Device properties created::

    {
        "switched_on" : switches on and off 
    }

"""

from device import Device
from helpers.solar import solar
import random

MIN_INTERVAL_S = 30*60
MAX_INTERVAL_S = 5*60*60

class Bulb(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Bulb,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.power = params["bulb"].get("power", None)
        if type(self.power) == list:
            self.power = random.choice(self.power)
        self.set_property("switched_on", False)
        engine.register_event_in(random.randrange(MIN_INTERVAL_S, MAX_INTERVAL_S), self.tick_bulb, self, self)

    def comms_ok(self):
        return super(Bulb,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Bulb,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Bulb,self).close()

    # Private methods
    def tick_bulb(self, _):
        lon = float(self.properties.get("longitude"))
        lat = float(self.properties.get("latitude"))
        external_light = solar.sun_bright(self.engine.get_now(), lon, lat)
        if self.get_property("switched_on"):
            if external_light > 0:
                self.set_property("switched_on", False)
            else:
                if random.random() > 0.5:   # Quite likely to turn light off during the day
                    self.set_property("switched_on", False)
        else:   # Currently switched off
            if external_light < 0.2:
                self.set_property("switched_on", True)
            else:
                if random.random() > 0.8:   # Pretty likely to turn light on during the night
                    self.set_property("switched_on", True)
        if self.power:
            if self.get_property("switched_on"):
                self.set_property("power", self.power, always_send=False)
            else:
                self.set_property("power", 0, always_send=False)
        self.engine.register_event_in(random.randrange(MIN_INTERVAL_S, MAX_INTERVAL_S), self.tick_bulb, self, self)
