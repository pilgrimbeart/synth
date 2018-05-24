"""
pulsewave
=========
Generates a pulse-wave with programmable characteristics.
The transition argument is either a percentage (default to 50%) or an ISO8601 duration.

Arguments::

    {
        "interval" : the period of the cycle e.g. "PT10M"
        "transition" : (optional) the delay to the mid transition, as a percentage or interval "PT10M"
        "delay" : (optional) a time delay by which to shift the waveform
        "invert" : (optional) inverts the output
        "phase_absolute" : (optional) if true then phase is relative to Jan 1970 (so all similar functions will be aligned), otherwise to when timefunction is created
    }
"""


from timefunction import Timefunction
import isodate
import math

class Pulsewave(Timefunction):
    def __init__(self, engine, device, params):
        """<interval> is the length of a full cycle ____----
           <transition> is when the low-to-high transition happens - either a percentage e.g. "75%" or another ISO interval
           <delay> is the absolute amount that the start is delayed
           If <phase_absolute> then phase of period is relative to 00:00:00 1 Jan 1970, otherwise to when this device is created"""
        self.engine = engine
        self.interval = float(isodate.parse_duration(params["interval"]).total_seconds())
        if "transition" not in params:
            self.transition = 0.5 # Square wave by default
        else:
            if params["transition"].endswith("%"):
                self.transition = float(params["transition"][0:-1]) / 100.0
            else:
                self.transition = float(isodate.parse_duration(params["transition"]).total_seconds()) / self.interval
        assert (self.transition>=0) and (self.transition<self.interval), "Transition must be within interval"

        self.delay = float(isodate.parse_duration(params.get("delay", "PT0S")).total_seconds())
        self.phase_absolute = params.get("phase_absolute", False)
        self.invert = params.get("invert", False)
        self.initTime = engine.get_now()

    def state(self, t=None, t_relative=False):
        """Return either 0 or 1 depending on current (or given) time.
           If <t_relative> then forces t to be relative regardless of settings at init()"""
        if t is None:
            t = self.engine.get_now()
        if (not self.phase_absolute) and (not t_relative):
            t -= self.initTime
        t -= self.delay

        mod = (t % self.interval) / self.interval
        result = (mod >= self.transition)

        if self.invert:
            result = not result
            
        return [0,1][result]

    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        if not self.phase_absolute:
            t -= self.initTime
        t -= self.delay

        mod = (t % self.interval) / self.interval
        start_of_this_cycle = math.floor(t / self.interval) * self.interval
        if mod < self.transition:
            t2 = start_of_this_cycle + self.transition * self.interval
        else:
            t2 = start_of_this_cycle + self.interval

        if not self.phase_absolute:
            t2 += self.initTime
        t2 += self.delay

        return t2

    def period(self):
        return self.interval


class dummy_engine():
    def get_now(self):
        return 0.0

if __name__ == "__main__":
    print "Testing 100s squarewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S" })
    assert fn.state(t=0)==0
    assert fn.state(t=49.999999)==0
    assert fn.state(t=50)==1
    assert fn.state(t=99.999999)==1
    assert fn.state(t=100)==0
    assert fn.state(t=150)==1
    assert fn.state(t=200)==0

    assert fn.next_change(t=0)==50
    assert fn.next_change(t=49.999999)==50
    assert fn.next_change(t=50)==100
    assert fn.next_change(t=99.999999)==100
    assert fn.next_change(t=100)==150

    print "Testing 100s squarewave inverted"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S", "invert" : True })
    assert fn.state(t=0)==1
    assert fn.state(t=49.999999)==1
    assert fn.state(t=50)==0
    assert fn.state(t=99.999999)==0
    assert fn.state(t=100)==1
    assert fn.state(t=150)==0
    assert fn.state(t=200)==1

    assert fn.next_change(t=0)==50
    assert fn.next_change(t=49.999999)==50
    assert fn.next_change(t=50)==100
    assert fn.next_change(t=99.999999)==100
    assert fn.next_change(t=100)==150

    print "Testing 100s 50% pulsewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S", "transition" : "50%" })
    assert fn.state(t=0)==0
    assert fn.state(t=49)==0
    assert fn.state(t=49.999999)==0
    assert fn.state(t=50)==1
    assert fn.state(t=99.999999)==1
    assert fn.state(t=100)==0
    assert fn.state(t=150)==1
    assert fn.state(t=200)==0

    assert fn.next_change(t=0)==50
    assert fn.next_change(t=49.999999)==50
    assert fn.next_change(t=50)==100
    assert fn.next_change(t=99.999999)==100
    assert fn.next_change(t=100)==150

    print "Testing 100s 75% pulsewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S", "transition" : "75%" })
    assert fn.state(t=0)==0
    assert fn.state(t=50)==0
    assert fn.state(t=74.999999)==0
    assert fn.state(t=75)==1
    assert fn.state(t=99.999999)==1
    assert fn.state(t=100)==0

    assert fn.next_change(t=0)==75
    assert fn.next_change(t=74.999999)==75
    assert fn.next_change(t=75)==100
    assert fn.next_change(t=100)==175

    print "Testing 100s (75s:25s) pulsewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S", "transition" : "PT75S" })
    assert fn.state(t=0)==0
    assert fn.state(t=50)==0
    assert fn.state(t=74.999999)==0
    assert fn.state(t=75)==1
    assert fn.state(t=99.999999)==1
    assert fn.state(t=100)==0

    assert fn.next_change(t=0)==75
    assert fn.next_change(t=74.999999)==75
    assert fn.next_change(t=75)==100
    assert fn.next_change(t=100)==175
    assert fn.next_change(t=174.999999)==175
    assert fn.next_change(t=175)==200
    assert fn.next_change(t=200)==275

    print "Testing 100s (25%:75%) pulsewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT100S", "transition" : "25%" })
    assert fn.state(t=0)==0
    assert fn.state(t=24.999999)==0
    assert fn.state(t=25)==1
    assert fn.state(t=99.999999)==1
    assert fn.state(t=100)==0

    assert fn.next_change(t=0)==25
    assert fn.next_change(t=24.999999)==25
    assert fn.next_change(t=25)==100
    assert fn.next_change(t=99.999999)==100
    assert fn.next_change(t=100)==125
    assert fn.next_change(t=125)==200
    assert fn.next_change(t=200)==225

    print "Testing 60min (20min:40min) pulsewave"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT60M", "transition" : "PT20M" })
    assert fn.state(t=0)==0
    assert fn.state(t=20*60)==1
    assert fn.state(t=60*60)==0
    assert fn.state(t=80*60)==1

    assert fn.next_change(t=0)==20*60
    assert fn.next_change(t=20*60)==60*60
    assert fn.next_change(t=60*60)==80*60
    assert fn.next_change(t=80*60)==2*60*60

    print "Testing 60s (20s:40s) pulsewave with 10s delay"
    fn = Pulsewave(dummy_engine(), { "interval" : "PT60S", "transition" : "PT20S", "delay" : "PT10S" })
    assert fn.state(t=0)==1
    assert fn.state(t=9)==1
    assert fn.state(t=10)==0
    assert fn.state(t=20)==0
    assert fn.state(t=29)==0
    assert fn.state(t=30)==1
    assert fn.state(t=60)==1
    assert fn.state(t=69)==1
    assert fn.state(t=70)==0

    assert fn.next_change(t=0)==10  # Going true
    assert fn.next_change(t=10)==30
    assert fn.next_change(t=30)==70
    assert fn.next_change(t=70)==90
    assert fn.next_change(t=90)==130

    print "Testing 20mins (15m:5m) pulsewave with -5m delay"
    fn = Pulsewave(dummy_engine(),  { "interval" : "PT20M", "transition" : "PT15M", "delay" : "-PT5M" })
    assert fn.state(t=0*60)==0
    assert fn.state(t=5*60)==0
    assert fn.state(t=10*60)==1
    assert fn.state(t=15*60)==0
    assert fn.state(t=20*60)==0
    assert fn.state(t=25*60)==0
    assert fn.state(t=30*60)==1
    assert fn.state(t=35*60)==0
    assert fn.state(t=40*60)==0

    assert fn.next_change(t=0)==10*60  # Going true
    assert fn.next_change(t=10*60)==15*60
    assert fn.next_change(t=15*60)==30*60
    assert fn.next_change(t=30*60)==35*60
    assert fn.next_change(t=35*60)==50*60

    print "All tests passed"
