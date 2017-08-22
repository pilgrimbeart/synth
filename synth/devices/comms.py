from device import Device
import random
import isodate
import timewave

GOOD_RSSI = -50.0
BAD_RSSI = -120.0

class Comms(Device):
    def __init__(self, time, engine, update_callback, params):
        self.ok_comms = True
        self.comms_reliability = params["comms"].get("reliability", 1.0) # Either a fraction, or a string containing a specification of the trajectory
        self.comms_up_down_period = isodate.parse_duration(params["comms"].get("period", "P1D")).total_seconds()
        engine.register_event_in(0, self.tick_comms_up_down, self)
        super(Comms,self).__init__(time, engine, update_callback, params)   # Set ourselves up before others do, so comms up/down takes effect even on device "boot"

    def comms_ok(self):
        return super(Comms, self).comms_ok() and self.ok_comms

    def external_event(self, event_name, arg):
        super(Comms, self).external_event(event_name, arg)
        pass
    
    # Private methods

    def tick_comms_up_down(self, _):
        if isinstance(self.comms_reliability, (int,float)):   # Simple probability
            self.ok_comms = self.comms_reliability > random.random()
        else:   # Probability spec, i.e. varies with time
            relTime = self.engine.get_now() - self.engine.get_start_time()
            prob = timewave.interp(self.comms_reliability, relTime)
            if self.property_exists("rssi"): # Now affect comms according to RSSI
                rssi = self.get_property("rssi")
                radioGoodness = 1.0-(rssi-GOOD_RSSI)/(BAD_RSSI-GOOD_RSSI)   # Map to 0..1
                radioGoodness = 1.0 - math.pow((1.0-radioGoodness), 4)      # Skew heavily towards "good"
                prob *= radioGoodness
            self.ok_comms = prob > random.random()

        delta_time = random.expovariate(1.0 / self.comms_up_down_period)
        delta_time = min(delta_time, self.comms_up_down_period * 100.0) # Limit long tail
        self.engine.register_event_in(delta_time, self.tick_comms_up_down, self)


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
