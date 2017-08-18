from device import Device
import random
import timewave

GOOD_RSSI = -50.0
BAD_RSSI = -120.0

class Comms(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Comms,self).__init__(time, engine, updateCallback, params)
        self.commsReliability = params["comms"].get("reliability", 1.0) # Either a fraction, or a string containing a specification of the trajectory
        self.commsUpDownPeriod = params["comms"].get("period", 1*60*60*24)
        engine.register_event_in(0, self.tickCommsUpDown, self)

    def externalEvent(self, eventName, arg):
        super(Comms,self).externalEvent(eventName, arg)
        pass
    
    # Private methods
    
    def tickCommsUpDown(self, _):
        if isinstance(self.commsReliability, (int,float)):   # Simple probability
            self.commsOK = self.commsReliability > random.random()
        else:   # Probability spec, i.e. varies with time
            relTime = self.engine.get_now() - self.engine.get_start_time()
            prob = timewave.interp(self.commsReliability, relTime)
            if self.propertyExists("rssi"): # Now affect comms according to RSSI
                rssi = self.getProperty("rssi")
                radioGoodness = 1.0-(rssi-GOOD_RSSI)/(BAD_RSSI-GOOD_RSSI)   # Map to 0..1
                radioGoodness = 1.0 - math.pow((1.0-radioGoodness), 4)      # Skew heavily towards "good"
                prob *= radioGoodness
            self.commsOK = prob > random.random()

        deltaTime = random.expovariate(1.0 / self.commsUpDownPeriod)
        deltaTime = min(deltaTime, self.commsUpDownPeriod * 100.0) # Limit long tail
        self.engine.register_event_in(deltaTime, self.tickCommsUpDown, self)


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
