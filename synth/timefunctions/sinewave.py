"""
sinewave
========
Generates a sinusoidal wave of programmable period. 32 points are generated per cycle.

Arguments::

    {
        "period" : the period of the cycle e.g. "PT10M"
        (the above can be an array, in which case multiple sinewaves are generated and added. This can be useful for Fourier synthesis, modelling events which change on different timescale
         such as wind speeds. By mixing a sufficient number of waves, an effectively random signal can be generated, but one whose value can be calculated for any moment in time
         (unlike standard LFSR randomness generators which are iterative))
        "amplitude" : likewise
        "overall_amplitude" : (optional) scales the overall output
        "overall_offset" : (optional) sets the overall level of the output
        "sample_period" : (optional) if not specified, sinewave(s) are generated at a period which automatically ensures high-resolution.
                            But that might be more than you want, so you can force the period of generation
        "randomise_phase_by" : "$id" (optional) if specified, hashes the value of the named property to offset the phase by an effectively random amount (so multiple devices are all at different points in the cycle)
        "precision" : (optional) If specified, the precision of the output (1= integer, 10 = decimal place, 100 = two decimals)
    }
"""

from .timefunction import Timefunction
import isodate
import math

POINTS_PER_CYCLE = 32

class Sinewave(Timefunction):
    """Generates sinewaves of defined period"""
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        p = params.get("period", "P1D") # We accept a string or a list of strings
        self.periods = []     # But internally always operate on a list
        if type(p) == list:
            for i in p:
                self.periods.append(float(isodate.parse_duration(i).total_seconds()))
        else:
            self.periods.append(float(isodate.parse_duration(p).total_seconds()))
        if not "amplitude" in params:
            self.amplitudes = [1.0] * len(self.periods)
        else:
            a = params.get("amplitude")
            self.amplitudes = []
            if type(a) == list:
                for i in a:
                    self.amplitudes.append(i)
            else:
                self.amplitudes.append(a)
        self.overall_amplitude = params.get("overall_amplitude", 1.0)
        self.overall_offset = params.get("overall_offset", 0.0)
        self.sample_period = params.get("sample_period", None)
        if self.sample_period is not None:
            self.sample_period = float(isodate.parse_duration(self.sample_period).total_seconds())
        self.randomise_phase_by = params.get("randomise_phase_by", None)
        self.precision = params.get("precision", None)
        self.initTime = engine.get_now()

    def randomise_phase(self, t):
        if self.randomise_phase_by is None:
            return t
        return hash(self.device.get_property(self.randomise_phase_by)) + t

    def state(self, t=None, t_relative=False):
        """Return a sinewave."""
        if t is None:
            t = self.engine.get_now()
        if (not t_relative):
            t -= self.initTime
        t = self.randomise_phase(t)

        v = 0
        for p,a in zip(self.periods, self.amplitudes):
            v = v + math.sin((2 * math.pi * t) / float(p)) * a/2.0 + 0.5  # Always positive
        v /= len(self.periods)
        v = v * self.overall_amplitude + self.overall_offset
        if self.precision is not None:
            v = int(v * self.precision) / float(self.precision)
        return v
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        t -= self.initTime

        if self.sample_period is not None:
            t2 = t + self.sample_period
        else:
            t2 = [] # Find earliest next samplepoint
            for per in self.periods:
                p = float(per) / POINTS_PER_CYCLE
                t2.append(math.floor(t / p) * p + p)
            t2 = min(t2)

        t2 += self.initTime

        return t2

    def period(self):
        return float(self.period) / POINTS_PER_CYCLE

class dummy_engine():
    def get_now(self):
        return 0

if __name__ == "__main__":
    if False:
        print("Sinewave")
        s = Sinewave(dummy_engine(), None, { "period" : "P1D" })
        for t in range(0, 60*60*24, 60*60):  # A day in hours
            print(t, s.state(t))

    if True:
        print("Three sinewaves")
        s = Sinewave(dummy_engine(), None,
                {   "period" : ["PT24H", "PT12H", "PT6H"],
                    "amplitude" : [1.0, 0.5, 0.25]
                } 
                )
        for t in range(0, 60*60*24, 60*60):  # A day in hours
            print(t, s.state(t))

    if False:
        print("Many sinewaves")
        s = Sinewave(dummy_engine(), None,
                {   "period" : ["PT7M", "PT13M", "PT17M", "PT23M", "PT37M", "PT3H", "PT13H", "PT27H", "P3D", "P7D", "P13D"],
                    "overall_amplitude" : 15.0,
                    "overall_offset" : -3.5
                } 
                )
        for t in range(0, 60*60*24*30, 60*60):  # A month of minutes
            print(t, s.state(t))

    # Self-driven timing
    if True:
        print("Three self-timed sinewaves")
        s = Sinewave(dummy_engine(), None,
                {   "period" : ["PT24H", "PT12H", "PT6H"],
                     "amplitude" : [1.0, 0.5, 0.25]
                } 
                )
        t = 0
        for i in range(1000):
            v = s.state(t)
            print(t,",",v)
            t = s.next_change(t)
