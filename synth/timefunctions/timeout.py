"""
timeout
==============
Creates a value which changes after a random period of time, with the random choice dependent on the property id

Arguments::

    {
        "min_time" : "PT0M",
        "max_time" : "PT1H",
        "off_value" : 0.0,
        "on_value" : 7.0
    }
"""

from .timefunction import Timefunction
import isodate
import math
import random
from zlib import crc32
import logging
 
class Timeout(Timefunction):
    """Changes a value after a random period of time based on device id """
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.min_time_S = float(isodate.parse_duration(params.get("min_time","PT0H")).total_seconds())
        self.max_time_S = float(isodate.parse_duration(params.get("max_time","PT1H")).total_seconds())
        self.off_value = params.get("off_value", 0)
        self.on_value = params.get("on_value", 1)
        r = random.Random()
        r.seed(crc32(self.device.get_property("$id").encode("utf-8")) / 2**32)
        r.random()
        r.random()
        r.random()
        self.timeout_time = int(self.min_time_S + (self.max_time_S - self.min_time_S) * r.random()) # Make it an integer number of seconds, to avoid precision issues when we test exactly on the boundary
        # logging.info("Timeout: timeout_time = "+str(self.timeout_time))
        self.init_time = engine.get_now()

    def state(self, t=None, t_relative=False):
        if t==None:
            t = self.engine.get_now()
        t -= self.init_time

        timed_out = (t >= self.timeout_time) 
        return [self.off_value, self.on_value][timed_out]
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        orig_t = t
        t -= self.init_time

        if t < self.timeout_time: # Avoid precision issues
            # logging.info("next_change at t="+str(t)+" orig_t="+str(orig_t)+" returning "+str(self.init_time + self.timeout_time))
            return self.init_time + self.timeout_time
        else:
            return None

    def period(self):
        return float(self.timeout_time)

