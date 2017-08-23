from device import Device
import random
import isodate
import logging

class Heartbeat(Device):
    def __init__(self, time, engine, update_callback, params):
        """Simple metronomic heartbeat transmission so that server knows we're still here"""
        super(Heartbeat,self).__init__(time, engine, update_callback, params)
        self.heartbeat_interval = isodate.parse_duration(params["heartbeat"].get("interval", "PT10M")).total_seconds()
        self.engine.register_event_in(self.heartbeat_interval, self.tick_heartbeat, self)

    def comms_ok(self):
        return super(Heartbeat,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Heartbeat,self).external_event(event_name, arg)

    # Private methods
    
    def tick_heartbeat(self,_):
        self.do_comms({})
        self.engine.register_event_in(self.heartbeat_interval, self.tick_heartbeat, self)
        
