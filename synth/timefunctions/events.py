"""
events
=========
Generates an event randomly.

Arguments::

    {
        "value" : the value of the event (i.e. what the property gets set to when the event happens)
        "interval" : the average period of the event (ISO8601 e.g. PT3h). Varies randomly around that.
    }
"""


from timefunction import Timefunction
import isodate
import random

class Events(Timefunction):
    def __init__(self, engine, device, params):
        self.engine = engine
        self.value = params.get("value", "event")
        self.interval = float(isodate.parse_duration(params.get("interval", "PT1D")).total_seconds())
        self.first_time_through = True

    def state(self, t=None, t_relative=False):
        if self.first_time_through:
            self.first_time_through = False
            return None # We'll get called at the start of time to find out the initial state, which is "no event"
        else:
            return self.value

    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()

        delta = random.expovariate(1.0 / self.interval) # expovariate delivers long-tailed distribution between 0 and infinity, centred on given value
        return t + delta

    def period(self):
        delta = random.expovariate(1.0 / self.interval) # expovariate delivers long-tailed distribution between 0 and infinity, centred on given value
        return delta


