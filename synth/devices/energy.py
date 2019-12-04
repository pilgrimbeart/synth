"""
energy
=====
Simulates energy meter

Configurable parameters::

    {
        "opening_times" : (optional) "name of an opening-times pattern"
        "max_power" : (optional) maximum power level
        "baseload_power" : (optional) baseload power level (e.g. night-time)
        "power_variation" : (optional) how much "noise" on the reading
    }

Device properties created::

    {
        "kWh" : odometer
        "kW" : instantaneous
    }
"""
import random
import logging
import time

from .device import Device
from .helpers import opening_times as opening_times

ENERGY_READING_INTERVAL_S = 60 * 30
DEFAULT_OPENING_TIMES = "nine_to_five"
DEFAULT_MAX_POWER_KW = 10.0
DEFAULT_BASELOAD_POWER_KW = 2.0
DEFAULT_POWER_VARIATION_KW = 1.0

class Energy(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Energy,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.opening_times = params["energy"].get("opening_times", DEFAULT_OPENING_TIMES)
        self.max_power_kW = params["energy"].get("max_power", DEFAULT_MAX_POWER_KW)
        self.baseload_power_kW = params["energy"].get("baseload_power", DEFAULT_BASELOAD_POWER_KW)
        self.power_variation_kW = params["energy"].get("power_variation", DEFAULT_POWER_VARIATION_KW)
        if not self.property_exists("device_type"):
            self.set_property("device_type", "energy")
        self.set_property("kWh", int(random.random() * 100000))
        self.occupied_bodge = params["energy"].get("occupied_bodge", False)
        if self.occupied_bodge:
            self.set_property("occupied", False)    # !!!!!!!!!!! TEMP BODGE TO OVERCOME CLUSTERING PROBLEM
        self.engine.register_event_in(ENERGY_READING_INTERVAL_S, self.tick_reading, self, self)

    def comms_ok(self):
        return super(Energy,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Energy,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Energy,self).close()

    # Private methods
    def tick_reading(self, _):
        open_chance = opening_times.chance_of_occupied(self.engine.get_now(), self.opening_times)
        kW = self.baseload_power_kW + open_chance * (self.max_power_kW - self.baseload_power_kW - self.power_variation_kW/2.0)
        kW += random.random() * self.power_variation_kW
        kWh = self.get_property("kWh")
        kWh += kW * ENERGY_READING_INTERVAL_S / (60 * 60.0)

        kW = int(100 * kW) / 100.0   # Round
        kWh = int(100 * kWh) / 100.0

        self.start_property_group() # -->
        self.set_property("kW", kW)
        self.set_property("kWh", kWh)
        if self.occupied_bodge:
            self.set_property("occupied", not self.get_property("occupied"))    # !!!!!!!!!!! TEMP BODGE TO OVERCOME CLUSTERING PROBLEM
        self.end_property_group() # <--
        self.engine.register_event_in(ENERGY_READING_INTERVAL_S, self.tick_reading, self, self)

