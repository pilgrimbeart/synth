"""Commswave
   Takes comms up and down according to some time function
"""

from device import Device
from common import importer

class Commswave(Device):
    def __init__(self, time, engine, update_callback, params):
        fn_name = params["commswave"]["function"].keys()[0]
        fn_class = importer.get_class("timefunction", fn_name)
        self.timefunction = fn_class(engine, params["commswave"]["function"])
        """No need to "tick" these functions, as they can calculate their states at arbitrary times on demand"""
        # engine.register_event_at(self.timefunction.next_change(), self.tick_commswave, self)
        super(Commswave,self).__init__(time, engine, update_callback, params)

    def comms_ok(self):
        return super(Commswave, self).comms_ok() and self.timefunction.current_state()

    def external_event(self, event_name, arg):
        super(Commswave, self).external_event(event_name, arg)
        pass
    
    # Private methods

##    def tick_commswave(self, _):
##        self.ok_commswave = self.timefunction.current_state()
##        self.engine.register_event_at(self.timefunction.next_change(), self.tick_commswave, self)
