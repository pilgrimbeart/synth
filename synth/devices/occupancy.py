"""
occupancy
=====
Simulates occupancy sensor

Configurable parameters::

    {
    }

Device properties created::

    {
        "occupied" : true / false
    }
"""
import random
import logging
import time

from device import Device
import helpers.opening_times as opening_times

OCCUPANCY_POLL_INTERVAL_S = 60 * 15

class Occupancy(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Occupancy,self).__init__(instance_name, time, engine, update_callback, context, params)
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
        occupied = random.random() < opening_times.chance_of_occupied(self.engine.get_now())
        self.set_property("occupied", occupied, always_send=False)
        self.engine.register_event_in(OCCUPANCY_POLL_INTERVAL_S, self.tick_occupancy, self, self)

