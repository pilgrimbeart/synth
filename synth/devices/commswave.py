"""Commswave
   Takes comms up and down according to some time function
"""

from device import Device
from common import importer

class Commswave(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        fn_name = params["commswave"]["timefunction"].keys()[0]
        fn_class = importer.get_class("timefunction", fn_name)
        self.timefunction = fn_class(engine, params["commswave"]["timefunction"])
        """No need to "tick" these functions, as they can calculate their states at arbitrary times on demand"""
        # engine.register_event_at(self.timefunction.next_change(), self.tick_commswave, self)
        super(Commswave,self).__init__(instance_name, time, engine, update_callback, params)

    def comms_ok(self):
        return super(Commswave, self).comms_ok() and self.timefunction.state()

    def external_event(self, event_name, arg):
        super(Commswave, self).external_event(event_name, arg)

    def finish(self):
        super(Commswave,self).finish()    
    
    # Private methods

##    (we don't actually need to tick, as we can instantaneously look up timefunction state whenever we need to)
##    def tick_commswave(self, _):
##        self.ok_commswave = self.timefunction.state()
##        self.engine.register_event_at(self.timefunction.next_change(), self.tick_commswave, self)
