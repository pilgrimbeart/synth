"""
comms
=====
Simulates unreliable communications between device and service.
If a property "rssi" exists, this is used to further modify the reliability.

Configurable parameters::

    {
        "reliability" : 1.0     A fraction 0.0..1.0 or the word "rssi" to generate reliability from RSSI
        "period" :      P1D     Mean period with which device goes up and down [or RSSI varies, if being created] (has exponential tail with max 100x). Defaults to once a day
        "metronomic_period" : false    If true then the up/down period is EXACTLY the above (not random)
        "has_buffer" :  false          If true then the device buffers data while comms is down (else it throws it away)
        "unbuffered_properties" : ["propname",...] (optional) these properties will be lost (not buffered) when comms goes offline - means that e.g. heartbeat messages don't get magically restored after an outage
        "suppress_messages" : false    If true then wont emit log messages
    }

Device properties created::

    {
            "connected" : true/false     An MQTT-like connection indicator
    }
    
"""


from .device import Device
from .helpers import timewave
import random
import isodate
import logging

BEST_RSSI = -50.0
WORST_RSSI = -120.0
RSSI_KNEE = -80.0           # Below this, comms gets progressively less reliable
DEFAULT_CHANCE_ABOVE_KNEE = 0.95    # Chance of any comms being OK if above knee
DEFAULT_CHANCE_AT_WORST = 0.00      # Chance of any comms being OK if RSSI is at worst

class Comms(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.ok_comms = True
        self.comms_reliability = params["comms"].get("reliability", 1.0)    # 0..1 or the word "rssi"
        if self.comms_reliability == "rssi":
            rssi_span = BEST_RSSI-WORST_RSSI
            self.rssi_mean = WORST_RSSI + rssi_span*0.2 + random.random() * rssi_span*0.8   # Mean value for RSSI of any particular device lies between a fifth and four fifths of the range
            self.rssi_sigma = rssi_span/12 
            self.set_rssi()
        self.comms_up_down_period = isodate.parse_duration(params["comms"].get("period", "P1D")).total_seconds()
        self.comms_metronomic_period = params["comms"].get("metronomic_period", False)
        self.has_buffer = params["comms"].get("has_buffer", False)
        self.suppress_messages = params["comms"].get("suppress_messages", False)
        self.unbuffered_properties = params["comms"].get("unbuffered_properties", [])
        self.chance_above_knee = params["comms"].get("reliability_above_rssi_knee", DEFAULT_CHANCE_ABOVE_KNEE)
        self.chance_at_worst = DEFAULT_CHANCE_AT_WORST
        self.buffer = []
        self.messages_attempted = 0
        self.messages_sent = 0
        self.messages_delayed = 0
        super(Comms,self).__init__(instance_name, time, engine, update_callback, context, params)   # Chain other classes last, so we set ourselves up before others do, so comms up/down takes effect even on device "boot"
        engine.register_event_in(0, self.tick_comms_up_down, self, self)
        self.set_property("connected", True)

    def comms_ok(self): # Overrides base-class's definition
        return super(Comms, self).comms_ok() and self.ok_comms

    def transmit(self, the_id, ts, properties, force_comms):
        self.messages_attempted += 1
        # logging.info("comms.py::transmit")
        if self.ok_comms or force_comms:
            if self.comms_reliability == "rssi":
                properties["rssi"] = self.rssi  # Add an RSSI property to any outgoing messages
            super(Comms, self).transmit(the_id, ts, properties, force_comms)
            self.messages_sent += 1
            # logging.info("(doing comms)")
        else:
            if self.has_buffer:
                self.messages_delayed += 1
                for p in self.unbuffered_properties:
                    if p in properties:
                        logging.info("Throwing-away unbuffered property "+str(p))
                        del properties[p]
                self.buffer.append( (the_id, ts, properties) )
            else:
                pass # Discard data
                 
    def external_event(self, event_name, arg):
        super(Comms, self).external_event(event_name, arg)

    def close(self):
        logging.info("Comms report for " + str(self.properties["$id"]) + " " +
                str(self.messages_sent) + " sent ("+str(100 * self.messages_sent/self.messages_attempted) + "%) and " +
                str(self.messages_delayed) + " delayed ("+str(100 * self.messages_delayed/self.messages_attempted) + "%) of " +
                str(self.messages_attempted) + " total")
        super(Comms,self).close()

    # Private methods

    def set_rssi(self):
        self.rssi = random.normalvariate(self.rssi_mean, self.rssi_sigma)
        self.rssi = min(self.rssi, BEST_RSSI)
        self.rssi = max(self.rssi, WORST_RSSI)
        self.rssi = int(self.rssi)
        # print "rssi_mean=",self.rssi_mean,"rssi_sigma=",self.rssi_sigma,"so rssi=",self.rssi

    def is_rssi_good_enough(self):
        if self.rssi > RSSI_KNEE:
            result = random.random() < self.chance_above_knee
            # print "self.rssi = ",self.rssi,"which is above knee, so result is",result
            return result
        else:
            chance = float(self.rssi - WORST_RSSI)/(RSSI_KNEE-WORST_RSSI)   # normalise our position on line from worst to knee
            chance = self.chance_at_worst + chance * (self.chance_above_knee - self.chance_at_worst) 
            result = random.random() < chance
            # print "self.rssi = ",self.rssi,"which is below knee, so result is",result
            return result

    def change_comms(self, ok):
        if ok and (not self.ok_comms): # Comms coming back online
            self.ok_comms = True
            self.set_property("connected", True)    # Send this *after* restoring comms!
            if not self.suppress_messages:
                logging.info("comms.py: comms coming back online for device "+str(self.properties["$id"]))
            if self.has_buffer:
                if not self.suppress_messages:
                    logging.info("comms.py: ... so now transmitting " + str(len(self.buffer)) + " buffered events")
                for e in self.buffer:   # Transmit everything stored while we were offline
                    self.transmit(e[0],e[1],e[2], True)
                self.buffer = []

        if (not ok) and self.ok_comms:  # Comms going offline
            self.set_property("connected", False)   # Send this *before* stopping comms!
            self.ok_comms = False
            if not self.suppress_messages:
                logging.info("comms.py: comms going offline for device " + str(self.properties["$id"]))

    def tick_comms_up_down(self, _):
        if isinstance(self.comms_reliability, (int,float)):   # Simple probability
            self.change_comms(self.comms_reliability > random.random())
        elif self.comms_reliability=="rssi":
            self.set_rssi()
            self.change_comms(self.is_rssi_good_enough())
        else:
            assert False, "comms_reliability spec of "+str(self.comms_reliability)+" not supported"

        if self.comms_metronomic_period:
            delta_time = self.comms_up_down_period
        else:
            delta_time = random.expovariate(1.0 / self.comms_up_down_period)
            delta_time = max(delta_time, 60.0) # never more than once a minute
            delta_time = min(delta_time, self.comms_up_down_period * 10.0) # Limit long tail
        self.engine.register_event_in(delta_time, self.tick_comms_up_down, self, self)

# Model for comms unreliability
# -----------------------------
# Two variables define comms (un)reliability:
# a) updownPeriod: (secs) The typical period over which comms might change between working and failed state. We use an exponential distribution with this value as the mean.
# b) reliability: (0..1) The chance of comms working at any moment in time
# The comms state is then driven independently of other actions.
# 
# Chance of comms failing at any moment is [0..1]
# Python function random.expovariate(lambd) returns values from 0 to infinity, with most common values in a hump in the middle
# such that that mean value is 1.0/<lambd>
