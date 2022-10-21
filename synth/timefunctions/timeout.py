"""
timeout
==============
Creates a value which changes after a random period of time, with the random choice dependent on the property id

Arguments::

    {
        "min_time" : "PT0M",
        "max_time" : "PT1H",
        "off_value" : 0.0,
        "on_value" : 7.0,
        "period" : "PT2H" (optional) - reset after this time
        "denominator" : 50  (optional) - if specified, then devices turn on non-randomly such that this many devices will be on by max_time
        "metronomic" : "PT5M" (optional) - if specified, only emits values at this time interval, and always does
    }
"""

if __name__ == "__main__":
    from timefunction import Timefunction
else:
    from .timefunction import Timefunction
import isodate
import math
import random
from zlib import crc32
import logging
 
class Timeout(Timefunction):
    """Changes a value after a random period of time based on device id """
    __device_count = 0
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.min_time_S = float(isodate.parse_duration(params.get("min_time","PT0H")).total_seconds())
        self.max_time_S = float(isodate.parse_duration(params.get("max_time","PT1H")).total_seconds())
        self.off_value = params.get("off_value", 0)
        self.on_value = params.get("on_value", 1)
        if "period" in params:
            self.period = float(isodate.parse_duration(params["period"]).total_seconds())
        else:
            self.period = None
        self.denominator = params.get("denominator", None)
        if "metronomic" in params:
            self.metronomic = isodate.parse_duration(params["metronomic"]).total_seconds()
        else:
            self.metronomic = None

        if self.denominator:    # Turn on predictably
            self.timeout_time = int(self.min_time_S + (self.max_time_S - self.min_time_S) * Timeout.__device_count / self.denominator)
            Timeout.__device_count += 1
        else:                   # Turn on randomly
            r = random.Random()
            r.seed(crc32(self.device.get_property("$id").encode("utf-8")) / 2**32)
            r.random()
            r.random()
            r.random()
            self.timeout_time = int(self.min_time_S + (self.max_time_S - self.min_time_S) * r.random()) # Make it an integer number of seconds, to avoid precision issues when we test exactly on the boundary

        self.init_time = engine.get_now()

    def state(self, t=None, t_relative=False):
        if t==None:
            t = self.engine.get_now()
        t -= self.init_time
        if self.period:
            t = t % self.period

        timed_out = (t >= self.timeout_time) 
        return [self.off_value, self.on_value][timed_out]
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        t -= self.init_time

        if self.metronomic:
            return self.init_time + (int(t / self.metronomic) + 1) * self.metronomic

        if self.period is None:
            if t < self.timeout_time: # Avoid precision issues
                return self.init_time + self.timeout_time
            else:
                return None
        else:
            cycles=    int(t / self.period)
            fraction = t % self.period
            if fraction < self.timeout_time:  # Waiting for timeout
                return self.init_time + cycles * self.period + self.timeout_time
            else:                       # Waiting for end-of-period reset
                return self.init_time + (cycles+1) * self.period

    def period(self):
        if self.period is not None:
            return self.period
        else:
            return float(self.timeout_time)

class dummy_engine():
    def get_now(self):
        return 0.0


class dummy_device():
    def get_property(self, p):
        assert p=="$id"
        return "ABC"

if __name__ == "__main__":
    print("Testing non-periodic")
    fn = Timeout(dummy_engine(), dummy_device(), { "min_time" : "PT25S", "max_time" : "PT50S", "off_value" : False, "on_value" : True })
    assert fn.state(t=0)==False
    assert fn.state(t=24)==False
    assert fn.state(t=51)==True
    assert fn.state(t=9e99)==True

    assert 25 <= fn.next_change(t=0) <= 50
    assert fn.next_change(t=50) == None # No events after timeout

    print("Testing periodic")
    fn = Timeout(dummy_engine(), dummy_device(), { "min_time" : "PT25S", "max_time" : "PT50S", "period" : "PT100S", "off_value" : False, "on_value" : True })
    assert fn.state(t=0)==False
    assert fn.state(t=24)==False
    assert fn.state(t=51)==True
    assert fn.state(t=100)==False
    assert fn.state(t=124)==False
    assert fn.state(t=151)==True
    assert fn.state(t=200)==False

    assert 25 <= fn.next_change(t=0) <= 50
    assert fn.next_change(t=50) == 100
    assert 125 <= fn.next_change(t=100) <= 150
    assert fn.next_change(t=150) == 200

    print("Testing metronomic and denominator")
    fn = Timeout(dummy_engine(), dummy_device(), { "min_time" : "PT10S", "max_time" : "PT50S", "period" : "PT100S", "off_value" : False, "on_value" : True, "denominator" : 3, "metronomic" : "PT60S" })
    assert fn.state(t=10)==True
    assert fn.next_change(t=0) == 60
    assert fn.next_change(t=30) == 60
    assert fn.next_change(t=60) == 120

    print("Passed")
