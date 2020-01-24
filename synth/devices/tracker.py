"""
tracker
=====
Tracks a target value in a controlled way. Can be used to simulate patterns of e.g. heating or cooking etc.

Configurable parameters::

    {
        output_property : "temp" (or whatever)
        min_value :             Minimum value of output
        max_value :             Maximum value of output
        max_value_twosigma :    Error in max value (static random number per device). Will never be bigger than +/- this amount
        noise :                 Ongoing noise added to value (varies slowly)
        precision :             Precision of output (e.g. 1 for integers, 10 for decades)
        opening_times : ["Mo-Fr 09:00-12:00", "Mo-Su"]      The opening times which drive activity
        smoothing_alpha : 0..1  (smaller means tracks slower, 1 means tracks with no smoothing)
        period :                Period of output, as ISO8601 period (e.g. "PT15M" for every 15 minutes")
        randomness_property     Name of the property to use to get randomness (so if for example you want all devices at one location to share randomness, refer to the 'location' property here)
    }

Device properties created::

    {
        <output_property>
    }
"""
import random
import logging
import time
import isodate
from math import sin, pi

from .device import Device
from common import opening_times

DEFAULT_PERIOD = "PT15M"
DEFAULT_VARIABILITY_BY_DEVICE = 0.2

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24

def hash_to_0_1(v, n):
    # v is a value to derive a random number from (can be anything at all - a number, a string etc.)
    # n is an integer which says which random number we want, e.g. 0 is the first random number, 1 is the second
    r = random.Random()
    r.seed(v)
    r.random()
    r.random()
    for i in range(n):
        r.random()
    result = r.random()
    return result

def frequency_noise(t):
    h = 2 * pi * t/HOURS    # Convert seconds into hours, and radians
    v = sin(h) + sin(h/1.3) + sin(h/2.7) + sin(h/7.7) + sin(h/13.3) + sin(h/29.3) + sin(h/47)
    v = (v + 1.0) / 2.0
    return v    # Return 0..1

class Tracker(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Tracker,self).__init__(instance_name, time, engine, update_callback, context, params)
        args = params["tracker"]
        self.randomness_property = args.get("randomness_property", None)
        self.my_random = random.Random() # We use our own random-number generator, one per variable per device
        if self.randomness_property is None:
            self.my_random.seed(self.get_property("$id"))   # Seed each device uniquely
        else:
            self.my_random.seed(hash(self.get_property(self.randomness_property)))

        open_t = args.get("opening_times")
        if isinstance(open_t, list):
            open_t = open_t[self.my_random.randrange(len(open_t))]  # Choose one of the options
        self.set_property("opening_times", open_t)
        self.opening_times = opening_times.parse(open_t)

        self.output_property = args.get("output_property", "tracker")
        self.min_value = args.get("min_value", 0)
        mx = args.get("max_value", 100)
        mxs = args.get("max_value_twosigma", 0)
        self.max_value = random.gauss(mx, mxs/2)
        self.max_value = min(self.max_value, mx+mxs)
        self.max_value = max(self.max_value, mx-mxs)
        self.noise_level = args.get("noise", 0)
        self.precision = args.get("precision", 1)
        self.smoothing_alpha = args.get("smoothing_alpha", 0.1)
        self.polling_interval = isodate.parse_duration(args.get("period", DEFAULT_PERIOD)).total_seconds()
        self.tracking_value = None
        self.time_offset = None

        self.set_property(self.output_property, self.current_value())
        self.engine.register_event_in(self.polling_interval, self.tick_update, self, self)

    def comms_ok(self):
        return super(Tracker,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Tracker,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Tracker,self).close()

    # Private methods
    def tick_update(self, _):
        self.set_properties({
            self.output_property : self.current_value(),
            "open" : opening_times.is_open(self.engine.get_now(), self.opening_times)
            })
        self.engine.register_event_in(self.polling_interval, self.tick_update, self, self)

    def fixed_random(self, v, n):   # TODO: This "delay generation of randomness until our randomness_property has been set" behaviour is no longer required, now that we can specify init order in scenario files using "name:N" format
        if v is not None:
            return v

        if self.property_exists(self.randomness_property):
            return hash_to_0_1(self.get_property(self.randomness_property), n)

        return None # We can't operate

    def current_value(self):
        self.time_offset = self.fixed_random(self.time_offset, 0)

        now = self.engine.get_now() + (self.time_offset - 0.5) * 60 * 60 * 2 # Add +/- 1h of shift to opening times
        open = opening_times.is_open(now, self.opening_times) 
        if open:
            a = 1.0
        else:
            a = 0.0

        target = self.min_value + a * (self.max_value - self.min_value) 

        if self.tracking_value is None:
            self.tracking_value = target
        else:
            self.tracking_value = self.tracking_value * (1-self.smoothing_alpha) + target * self.smoothing_alpha

        fnoise = frequency_noise(self.engine.get_now() + hash(self.get_property("$id")))  # Each device has different frequency noise phase
        result = self.tracking_value + fnoise * self.noise_level

        return int(result / self.precision) * self.precision

