"""
bytes
=====
Provides a device property which sends back the number of bytes sent

Configurable parameters::

    {
    }

Device properties created::

    {
        "bytes_sent" : Bytes sent in the last period
    }

"""

from .device import Device
import logging

BYTECOUNT_SEND_INTERVAL_S = 60 * 60

class Bytes(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.bytes_sent_this_interval = 0
        super(Bytes,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.engine.register_event_in(BYTECOUNT_SEND_INTERVAL_S, self.tick_sendbytes, self, self)

    def comms_ok(self):
        return super(Bytes,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Bytes,self).external_event(event_name, arg)

    def close(self):
        super(Bytes,self).close()

    def transmit(self, the_id, ts, properties, force_comms):
        super(Bytes, self).transmit(the_id, ts, properties, force_comms)
        self.bytes_sent_this_interval += len(str(properties))

    def tick_sendbytes(self, _):
        self.set_property("bytes_sent", self.bytes_sent_this_interval)
        self.bytes_sent_this_interval = 0
        self.engine.register_event_in(BYTECOUNT_SEND_INTERVAL_S, self.tick_sendbytes, self, self)
