"""
carbon
=======
Fetches carbon intensity of grid

Device properties created::

    {
        "carbon_intensity" : N  # in gCO2/kWh
    }
"""

from .device import Device
from .helpers import grid_carbon
import logging

class Carbon(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Carbon,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.read_intensity()
        engine.register_event_at(grid_carbon.next_tick(self.engine.get_now()), self.tick_reading, None, self)

    def comms_ok(self):
        return super(Carbon,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Carbon,self).external_event(event_name, arg)

    def close(self):
        super(Carbon,self).close()

    def read_intensity(self):
        self.set_property("carbon_intensity", grid_carbon.get_intensity(self.engine.get_now()))

    def tick_reading(self, _):
        self.read_intensity()
        self.engine.register_event_at(grid_carbon.next_tick(self.engine.get_now()), self.tick_reading, None, self)
