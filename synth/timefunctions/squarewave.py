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

    def current_state(self):
        """Return either 0 or 1"""
        t = self.engine.get_now()
        if self.phase_relative:
            t -= self.initTime
        half = self.interval / 2.0
	v = int(t / half) % 2
        return v

    def next_change(self):
        """Return a future time when the next event will happen"""
        t = self.engine.get_now()
        if self.phase_relative:
            t -= self.initTime
        half = self.interval / 2.0
        return int(t / half)*half + half
