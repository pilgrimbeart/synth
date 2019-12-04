"""
count
=======
Generates a monotonically rising count at defined intervals.

Arguments::

    {
        "interval" : the time between counts
        "modulo" : (optional) the point at which to wrap - if unspecified, never wraps
    }
"""


from .timefunction import Timefunction
import isodate
import math

class Count(Timefunction):
    def __init__(self, engine, device, params):
        """<interval> is the length between counts"""
        self.engine = engine
        self.interval = float(isodate.parse_duration(params["interval"]).total_seconds())
        self.modulo = params.get("modulo", None)

        self.init_time = engine.get_now()

    def state(self, t=None, t_relative=False):
        """Return count of intervals since init"""
        if t is None:
            t = self.engine.get_now()

        v = int((t-self.init_time) / self.interval)
        if self.modulo is not None:
            v = v % self.modulo
        return v

    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()

        t2 = int(t / self.interval) * self.interval + self.interval

        return t2

    def period(self):
        return self.interval


class dummy_engine():
    def get_now(self):
        return 0.0

