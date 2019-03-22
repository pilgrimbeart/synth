"""
sump
=====
Simulates a sump, managed by a water pump (e.g. pumping accumulated surface water out of storm drains, or similar)
Requires that device has property "precipitation_intensity" in mm/hr, as created by "weather"

Configurable parameters::

    {
    }

Device properties created::

    {
        sump_level_mm : mm of water
        sump_limit_mm :
        sump_pump_energy_consumption_kW
    }

"""

from device import Device
import random

CHECK_INTERVAL_S = 60*60
MIN_SUMP_LIMIT = 5
MAX_SUMP_LIMIT = 15
SUMP_DRAIN_RATE_MM_HR = 0.39
SUMP_ENERGY_CONSUMPTION_KW = 2.7

class Pump(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Pump,self).__init__(instance_name, time, engine, update_callback, context, params)
        engine.register_event_in(0, self.tick_pump, self, self)
        self.set_property("sump_level_mm", 0)
        self.set_property("sump_limit_mm",
                int(MIN_SUMP_LIMIT + random.random() * (MAX_SUMP_LIMIT-MIN_SUMP_LIMIT)))

    def comms_ok(self):
        return super(Pump,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Pump,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Pump,self).close()

    # Private methods
    def tick_pump(self, _):
        precip = self.get_property("precipitation_intensity", 0)
        level = self.get_property("sump_level_mm")
        limit = self.get_property("sump_limit_mm")
        level = level + precip
        if level > 0:
            self.set_property("sump_pump_energy_consumption_kW", min(1.0, float(level) / SUMP_DRAIN_RATE_MM_HR) * SUMP_ENERGY_CONSUMPTION_KW)    # Run pump for long-enough to drain the sump
            level = max(0.0, level - SUMP_DRAIN_RATE_MM_HR)
        else:
            self.set_property("sump_pump_energy_consumption_kW", 0.0, always_send=False)
        self.set_property("sump_level_mm", level, always_send=False)

        self.engine.register_event_in(CHECK_INTERVAL_S, self.tick_pump, self, self)

