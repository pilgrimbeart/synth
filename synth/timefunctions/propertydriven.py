"""
propertydriven
==============
Creates a value between 0 and 1 which is random but derived from a device property and unchanging over time. So the value doesn't change is the property value doesn't change.
E.g. this can be used to give each device a random cellular signal strength which is different for each device, but constant for that device.
E.g. if the property is e.g. an enumerated type, such as hardware version, then the value will be the same for all devices that share the same hardware version.

Arguments::

    {
        "property_name" : the name of the property to use as a random seed [defaults to $id]
    }
"""

from .timefunction import Timefunction
import isodate
import math
import random
import logging
 
class Propertydriven(Timefunction):
    """Generates a random value based on a property value"""
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.period = float(isodate.parse_duration(params.get("period","PT24H")).total_seconds())    # Since our value doesn't change, period is rather meaningless, but we have to be able to report a "next_change" time.
        self.initTime = engine.get_now()
        self.driving_property_name = params.get("property", "$id")

    def state(self, t=None, t_relative=False):
        """Return a random value based on a property. Doesn't vary over time."""

        r = random.Random() # Our own private random number generator
        r.seed(hash(self.device.get_property(self.driving_property_name)))
        r.random()
        r.random()
        r.random()
        return r.random()
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        if t is None:
            t = self.engine.get_now()
        t -= self.initTime

        p = float(self.period)
        t2 = math.floor(t / p) * p + p

        t2 += self.initTime

        return t2

    def period(self):
        return float(self.period)

