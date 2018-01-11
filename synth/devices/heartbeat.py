"""
heartbeat
=========
Forces the device to communicate at regular intervals so that communications timeouts can be detected by the service.
Doesn't set any properties.

Configurable parameters::

    {
        "interval" : as an ISO8601 duration e.g. "PT10M"
    }

Device properties created::

    {
    }

"""

from device import Device
import random
import isodate
import logging

class Heartbeat(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """Simple metronomic heartbeat transmission so that server knows we're still here"""
        super(Heartbeat,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.heartbeat_interval = isodate.parse_duration(params["heartbeat"].get("interval", "PT10M")).total_seconds()
        self.engine.register_event_in(self.heartbeat_interval, self.tick_heartbeat, self, self)

    def comms_ok(self):
        return super(Heartbeat,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Heartbeat,self).external_event(event_name, arg)

    def close(self):
        super(Heartbeat, self).close()

    # Private methods
    
    def tick_heartbeat(self,_):
        self.do_comms({})
        self.engine.register_event_in(self.heartbeat_interval, self.tick_heartbeat, self, self)
        
