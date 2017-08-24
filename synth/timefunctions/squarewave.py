from timefunctions.timefunction import Timefunction
import isodate

class Squarewave(Timefunction):
    def __init__(self, engine, params):
        self.engine = engine
        self.interval = isodate.parse_duration(params["squarewave"]["interval"]).total_seconds()
        self.phase_relative = params["squarewave"].get("phase_relative", False)
        self.initTime = engine.get_now()
        """<interval> is the length of both an up AND a down
           If <phase_relative> then phase of period is relative to simulation start time, otherwise to 00:00:00 1 Jan 1970"""

    def state(self, t=None):
        """Return either 0 or 1"""
        if t is None:
            t = self.engine.get_now()
        if self.phase_relative:
            t -= self.initTime
        half = self.interval / 2.0
	v = int(t / half) % 2
        return v

    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()

        if self.phase_relative:
            t -= self.initTime

        half = self.interval / 2.0
        t2 = int(t / half)*half + half

        if self.phase_relative:
            t2 += self.initTime

        return t2
