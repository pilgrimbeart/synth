"""
commswave
=========
Takes device communications up and down according to a timefunction.
Comms will be working whenever the timefunction returns non-zero.

Configurable parameters::

    {
        "timefunction" : A timefunction definition
        "threshold" : (optional) Comms will only work when the timefunction is returning >= threshold. If missing then any non-zero value will make comms work.
        "gate_properties" : (optional) ["list", "of", "properties"]  If this is defined, then instead of taking whole comms up and down, only these specific properties are gated
    }

Device properties created::

    {
        "connected" : A flag which shows if we are currently connected (TCP- and therefore MQTT-like)
    }

"""

from .device import Device
from common import importer
import logging
import inspect

class Commswave(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """Take Comms up and down according to some time function"""
        tf = params["commswave"]["timefunction"]
        self.comms_timefunction = importer.get_class("timefunction", list(tf.keys())[0])(engine, self, tf[list(tf.keys())[0]])
        self.comms_tf_threshold = params["commswave"].get("threshold", None)
        self.comms_gate_properties = params["commswave"].get("gate_properties", None)
        self.messages_sent = 0
        self.messages_attempted = 0
        super(Commswave,self).__init__(instance_name, time, engine, update_callback, context, params)   # This may send messages (calling our comms_ok() and transmit() functions), so we need to be set-up-enough before calling it
        self.set_property("connected", self.timefunction_says_communicate())
        self.engine.register_event_at(self.comms_timefunction.next_change(), self.tick_commswave, self, self) # Tick the "connected" flag 

    def timefunction_says_communicate(self):
        thresh = 0.0
        if self.comms_tf_threshold is not None:
            thresh = self.comms_tf_threshold
        return self.comms_timefunction.state() > thresh

    def comms_ok(self):
        if self.comms_gate_properties is not None:  # If we're gating individual properties, then don't gate overall comms
            return super(Commswave, self).comms_ok()
        else:
            self.messages_attempted += 1
            is_ok = super(Commswave, self).comms_ok()
            is_ok = is_ok and self.timefunction_says_communicate()
            if is_ok:
                self.messages_sent += 1
            return is_ok

    def transmit(self, the_id, ts, properties, force_comms):
        if self.comms_gate_properties is not None:  # We're gating properties
            if not self.timefunction_says_communicate():
                for p in self.comms_gate_properties:
                    properties.pop(p, None) # Remove the property, if it's there

        # logging.info("commswave.transmit("+str(properties)+") called from "+str(inspect.stack()[1]))
        super(Commswave, self).transmit(the_id, ts, properties, force_comms)

    def external_event(self, event_name, arg):
        super(Commswave, self).external_event(event_name, arg)

    def close(self):
        super(Commswave,self).close()
        logging.info("Comms report for " + str(self.properties["$id"]) + " " +
            str(self.messages_sent) + " sent ("+str(100 * self.messages_sent/self.messages_attempted) + "%) from " +
            str(self.messages_attempted) + " total")


    # Private methods

    def tick_commswave(self, _):
        state = self.timefunction_says_communicate()
        logging.info("commswave: comms going " + ["offline","online"][state] + " for device " + str(self.properties["$id"]))
        self.set_property("connected", state, force_send=True)  # We have to force send, because otherwise the fact that we've just set connected to false will cause our own comms_ok() function to prevent this transmission!
        self.engine.register_event_at(self.comms_timefunction.next_change(), self.tick_commswave, self, self)
