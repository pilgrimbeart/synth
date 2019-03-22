"""
randomwave
========
Generates a random value between 0 and 1, of programmable period.

Arguments::

    {
        "period" : the period with which the random value is updated e.g. "PT10M"
        "lower" : (optional) numbers will be returned within range (lower,upper)
        "upper" : (optional)
        "precision" : (optiona) 1 for integer, 10 for 1 decimal point, 100 for 2 decimals etc.
    }
"""

from timefunction import Timefunction
import isodate
import math
import random

# Because any time-function has to be able to generate the value of its waveform instantaneously for any moment
# in time, we cannot iterate to produce randomness (e.g. LFSR).
 
class Randomwave(Timefunction):
    """Generates random waves of defined period"""
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.period = float(isodate.parse_duration(params["period"]).total_seconds())
        self.lower = params.get("lower", 0.0)
        self.upper = params.get("upper", 1.0)
        self.precision = params.get("precision", None)
        self.initTime = engine.get_now()

    def state(self, t=None, t_relative=False):
        """Return a sinewave."""
        if t is None:
            t = self.engine.get_now()
        if (not t_relative):
            t -= self.initTime

        r = random.Random() # Our own private random number generator
        r.seed(t + hash(self.device.get_property("$id")))    # Unique per device
        r.random()
        r.random()
        r.random()
        v = self.lower + r.random() * (self.upper-self.lower)
        if self.precision is not None:
            v = int(v * self.precision) / float(self.precision)
        return v
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        t -= self.initTime

        p = float(self.period)
        t2 = math.floor(t / p) * p + p

        t2 += self.initTime

        return t2

    def period(self):
        return float(self.period)


# Check randomness
class dummy_engine():
    def get_now(self):
        return 0.0

if __name__ == "__main__":
    r = Randomwave(dummy_engine(), {"period" : "PT1S"})
    for t in xrange(1000):
        print r.state(t/10.0)
    
    
