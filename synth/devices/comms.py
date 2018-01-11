"""
comms
=====
Simulates unreliable communications between device and service.
If a property "rssi" exists, this is used to further modify the reliability.

Configurable parameters::

    {
        "reliability" : Either a fraction 0.0..1.0, or a string containing a specification of the trajectory. Defaults to 1.0
        "period" : Mean period with which device goes up and down (has exponential tail with max 100x). Defaults to once a day
        "has_buffer" : If this boolean is true then the device buffers data while comms is down (else it throws it away)
    }

Device properties created::

    {
    }
    
"""


from device import Device
import random
import isodate
import helpers.timewave
import logging

GOOD_RSSI = -50.0
BAD_RSSI = -120.0

class Comms(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.ok_comms = True
        self.comms_reliability = params["comms"].get("reliability", 1.0)
        self.comms_up_down_period = isodate.parse_duration(params["comms"].get("period", "P1D")).total_seconds()
        self.has_buffer = params["comms"].get("has_buffer", False)
        self.buffer = []
        engine.register_event_in(0, self.tick_comms_up_down, self, self)
        super(Comms,self).__init__(instance_name, time, engine, update_callback, context, params)   # Chain other classes last, so we set ourselves up before others do, so comms up/down takes effect even on device "boot"

    def comms_ok(self): # Overrides base-class's definition
        return super(Comms, self).comms_ok() and self.ok_comms

    def transmit(self, the_id, ts, properties, force_comms):
        # logging.info("comms.py::transmit")
        if self.ok_comms or force_comms:
            super(Comms, self).transmit(the_id, ts, properties, force_comms)
            # logging.info("(doing comms)")
        else:
            if self.has_buffer:
                # logging.info("(appending)")
                self.buffer.append( (the_id, ts, properties) )
            else:
                # logging.info("(discarding)")
                pass # Discard data
                 
    def external_event(self, event_name, arg):
        super(Comms, self).external_event(event_name, arg)

    def close(self):
        super(Comms,self).close()

    # Private methods

    def change_comms(self, ok):
        if ok and (self.ok_comms == False): # If restoring comms, transmit everything that buffered whilst comms was offline
            logging.info("comms.py: comms coming back online for device "+str(self.properties["$id"]))
            if self.has_buffer:
                logging.info("comms.py: ... so now transmitting " + str(len(self.buffer)) + " buffered events")
                for e in self.buffer:
                    self.transmit(e[0],e[1],e[2], True)
                self.buffer = []

        if (not ok) and self.ok_comms:
            logging.info("comms.py: comms going offline for device " + str(self.properties["$id"]))

        self.ok_comms = ok

    def tick_comms_up_down(self, _):
        if isinstance(self.comms_reliability, (int,float)):   # Simple probability
            self.change_comms(self.comms_reliability > random.random())
        else:   # Probability spec, i.e. varies with time
            relTime = self.engine.get_now() - self.creation_time
            prob = timewave.interp(self.comms_reliability, relTime)
            if self.property_exists("rssi"): # Now affect comms according to RSSI
                rssi = self.get_property("rssi")
                radioGoodness = 1.0-(rssi-GOOD_RSSI)/(BAD_RSSI-GOOD_RSSI)   # Map to 0..1
                radioGoodness = 1.0 - math.pow((1.0-radioGoodness), 4)      # Skew heavily towards "good"
                prob *= radioGoodness
            self.change_comms(prob > random.random())

        delta_time = random.expovariate(1.0 / self.comms_up_down_period)
        delta_time = min(delta_time, self.comms_up_down_period * 100.0) # Limit long tail
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
