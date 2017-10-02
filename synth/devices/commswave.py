"""
commswave
=========
Takes device communications up and down according to a timefunction.
Comms will be working whenever the timefunction returns non-zero.

Configurable parameters::

    {
        "timefunction" : A timefunction definition
    }

Device properties created::

    {
    }

"""

from device import Device
from common import importer

class Commswave(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        """Take Comms up and down according to some time function"""
        tf = params["commswave"]["timefunction"]
        self.comms_timefunction = importer.get_class("timefunction", tf.keys()[0])(engine, tf[tf.keys()[0]])
        super(Commswave,self).__init__(instance_name, time, engine, update_callback, params)

    def comms_ok(self):
        return super(Commswave, self).comms_ok() and self.comms_timefunction.state()

    def external_event(self, event_name, arg):
        super(Commswave, self).external_event(event_name, arg)

    def close(self, err_str):
        super(Commswave,self).close(err_str)

    # Private methods

##    (we don't actually need to tick, as we can instantaneously look up timefunction state whenever we need to)
##    def tick_commswave(self, _):
##        self.ok_commswave = self.comms_timefunction.state()
##        self.engine.register_event_at(self.comms_timefunction.next_change(), self.tick_commswave, self)
