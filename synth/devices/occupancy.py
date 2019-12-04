"""
occupancy
=====
Simulates occupancy sensor

Configurable parameters::

    {
        opening_times : "nine_to_five" (optional)
        peak_occupancy : 1.0 (optional)
        variability_by_device : 0.2 (optional)
    }

Device properties created::

    {
        "occupied" : true / false
    }
"""
import random
import logging
import time

from .device import Device
from .helpers import opening_times as opening_times

OCCUPANCY_POLL_INTERVAL_S = 60 * 15
DEFAULT_OPENING_TIMES = "nine_to_five"
DEFAULT_VARIABILITY_BY_DEVICE = 0.2

class Occupancy(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Occupancy,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.opening_times = params["occupancy"].get("opening_times", DEFAULT_OPENING_TIMES)
        self.peak_occupancy = params["occupancy"].get("peak_occupancy", 1.0)
        self.set_property("device_type", "occupancy")
        self.set_property("occupied", False)
        self.engine.register_event_in(OCCUPANCY_POLL_INTERVAL_S, self.tick_occupancy, self, self)

    def comms_ok(self):
        return super(Occupancy,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Occupancy,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Occupancy,self).close()

    # Private methods
    def tick_occupancy(self, _):
        occupied = random.random() < opening_times.chance_of_occupied(self.engine.get_now(), self.opening_times) * self.peak_occupancy
        self.set_property("occupied", occupied, always_send=False)
        self.engine.register_event_in(OCCUPANCY_POLL_INTERVAL_S, self.tick_occupancy, self, self)

