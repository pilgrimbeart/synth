"""
count
=======
Generates a monotonically rising count at defined intervals.

Arguments::

    {
        "interval" : the time between counts
        "increment" : how much to add each time
        "modulo" : (optional) the point at which to wrap - if unspecified, never wraps
        "stop_at" : stop generating values after this value is reached
    }
"""


from .timefunction import Timefunction
import isodate
import math
import logging

class Count(Timefunction):
    def __init__(self, engine, device, params):
        """<interval> is the length between counts"""
        self.engine = engine
        self.interval = float(isodate.parse_duration(params["interval"]).total_seconds())
        self.increment = params.get("increment", 1)
        self.modulo = params.get("modulo", None)
        self.stop_at = params.get("stop_at", None)

        self.init_time = engine.get_now()

    def state(self, t=None, t_relative=False):
        """Return count of intervals since init"""
        if t is None:
            t = self.engine.get_now()

        v = int((t-self.init_time) / self.interval) * self.increment
        if self.modulo is not None:
            v = v % self.modulo
        return v

    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()

        tOUT = int(t / self.interval) * self.interval + self.interval   # If called at intervals of (self.interval), will count 0,1,2...
        
        if self.stop_at:
            v = self.state()
            if v >= self.stop_at:
                return None

        return tOUT

    def period(self):
        return self.interval


class dummy_engine():
    def get_now(self):
        return 0.0

