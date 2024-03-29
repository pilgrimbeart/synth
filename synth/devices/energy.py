"""
energy
=====
Simulates energy meter (electricity or gas or both, with associated Comms module)

Configurable parameters::

    {
        "reading_interval" : (optional) "PT12H" - how often a reading is sent. Defaults to half-hourly.
        "opening_times" : (optional) "name of an opening-times pattern"
        "max_power" : (optional) maximum power level
        "baseload_power" : (optional) baseload power level (e.g. night-time)
        "power_variation" : (optional) how much "noise" on the reading
        "no_metadata" : (optional) don't send metadata
        "test_rate" : (optional) if true then kW starts at zero and rises forever (unless reset, below). [Numerator, Denominator] e.g. "[10, "PT10M"] means that the power will rise to 10kW after 10 minutes, and keep rising
        "reset_interval" : (optional) "PT4H" in test mode, when to reset
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
import isodate

from .device import Device
from .helpers import opening_times as opening_times

DEFAULT_ENERGY_READING_INTERVAL = "PT30M"
DEFAULT_OPENING_TIMES = "nine_to_five"
DEFAULT_MAX_POWER_KW = 10.0
DEFAULT_BASELOAD_POWER_KW = 2.0
DEFAULT_POWER_VARIATION_KW = 1.0

READING_FAULT_DAILY_CHANCE = 1.0 / 10000

TEST_MODE_INC_KW_PER_DAY = 1.0

class Energy(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Energy,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.start_time = engine.get_now()
        self.opening_times = params["energy"].get("opening_times", DEFAULT_OPENING_TIMES)
        self.max_power_kW = params["energy"].get("max_power", DEFAULT_MAX_POWER_KW)
        self.baseload_power_kW = params["energy"].get("baseload_power", DEFAULT_BASELOAD_POWER_KW)
        self.power_variation_kW = params["energy"].get("power_variation", DEFAULT_POWER_VARIATION_KW)
        self.no_metadata = params["energy"].get("no_metadata", False)
        if not "test_mode" in params["energy"]:
            self.test_mode = None
        else:
            (n,d) = params["energy"].get("test_mode")
            self.test_mode = float(n) / isodate.parse_duration(d).total_seconds()
        if "reset_interval" not in params["energy"]:
            self.reset_interval = None
        else:
            self.reset_interval = isodate.parse_duration(params["energy"]["reset_interval"]).total_seconds()
        if not self.property_exists("device_type"):
            if not self.no_metadata:
                self.set_property("device_type", "energy")
        if self.test_mode is not None:
            kWh = 0
        else:
            kWh = int(random.random() * 100000)
        self.set_properties({"kW" : 0, "kWh" : kWh})    # First kW reading is zero, so that integrating kW over time gives us kWh correctly
        self.occupied_bodge = params["energy"].get("occupied_bodge", False)
        if self.occupied_bodge:
            self.set_property("occupied", False)    # !!!!!!!!!!! TEMP BODGE TO OVERCOME CLUSTERING PROBLEM
        if not self.no_metadata:
            if random.random() > 0.5:
                self.set_properties({"meter_type" : "electricity", "icon" : "bolt"})
            else:
                self.set_properties({"meter_type" : "gas",  "icon" : "flame"})
        self.energy_reading_interval_s = isodate.parse_duration(params["energy"].get("reading_interval", DEFAULT_ENERGY_READING_INTERVAL)).total_seconds()
        self.engine.register_event_in(self.energy_reading_interval_s, self.tick_reading, self, self)

    def comms_ok(self):
        return super(Energy,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Energy,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Energy,self).close()

    # Private methods
    def tick_reading(self, _):
        if self.test_mode is not None:
            dT = self.engine.get_now() - self.start_time
            if self.reset_interval:
                dT = dT % self.reset_interval
            kW = dT * self.test_mode
        else:
            open_chance = opening_times.chance_of_occupied(self.engine.get_now(), self.opening_times)
            kW = self.baseload_power_kW + open_chance * (self.max_power_kW - self.baseload_power_kW - self.power_variation_kW/2.0)
            kW += random.random() * self.power_variation_kW

        kWh = self.get_property("kWh")
        kWh += kW * self.energy_reading_interval_s / (60 * 60.0)

        if self.test_mode is None:
            kW = int(1000 * kW) / 1000.0   # Round to 1 Watt
            kWh = int(100 * kWh) / 100.0

        reading_fault_chance = READING_FAULT_DAILY_CHANCE / ((60 * 60 * 24.0) / self.energy_reading_interval_s)
        if (self.test_mode is None) and (random.random() < reading_fault_chance):
            if random.random() > 0.5:
                delta = 1
            else:
                delta = -1
            delta *= random.randrange(1000,10000)    # Jump by at least 1000 (kWh, so if 30min readings that implies insane 2MW load!)
            logging.info("Energy meter reading fault on "+str(self.get_property("$id"))+" jumping by "+str(delta))
            kWh += delta

        self.start_property_group() # -->
        self.set_property("kW", kW)
        self.set_property("kWh", kWh)
        if self.occupied_bodge:
            self.set_property("occupied", not self.get_property("occupied"))    # !!!!!!!!!!! TEMP BODGE TO OVERCOME CLUSTERING PROBLEM
        self.end_property_group() # <--
        self.engine.register_event_in(self.energy_reading_interval_s, self.tick_reading, self, self)

