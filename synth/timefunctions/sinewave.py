"""
sinewave
========
Generates a sinusoidal wave of programmable period. 32 points are generated per cycle.

Arguments::

    {
        "period" : the period of the cycle e.g. "PT10M"
    }
"""

from timefunction import Timefunction
import isodate
import math

POINTS_PER_CYCLE = 32

class Sinewave(Timefunction):
    """Generates sinewaves of defined period"""
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.period = float(isodate.parse_duration(params["period"]).total_seconds())
        self.initTime = engine.get_now()

    def state(self, t=None, t_relative=False):
        """Return a sinewave."""
        if t is None:
            t = self.engine.get_now()
        if (not t_relative):
            t -= self.initTime

        return math.sin((2 * math.pi * t) / float(self.period)) * 0.5 + 0.5  # Always positive
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        t -= self.initTime

        p = float(self.period) / POINTS_PER_CYCLE
        t2 = math.floor(t / p) * p + p

        t2 += self.initTime

        return t2

    def period(self):
        return float(self.period) / POINTS_PER_CYCLE


