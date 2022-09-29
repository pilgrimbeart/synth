"""
mix
===
Combine timefunctions according to some operator.

Arguments::

    {
        "timefunctions" : [] an array of timefunctions
        "operator" : How to combine the timefunctions ("and", "add" and "mul" currently supported)
    }
"""

from .timefunction import Timefunction
from common import importer
from common.ordinal import LCMM
import logging

class Mix(Timefunction):
    """Combine timefunctions according to a given operator"""
    def __init__(self, engine, device, params):
        self.engine = engine
        self.device = device
        self.mix_operator = params["operator"]
        self.mix_timefunctions = []
        logging.info("Mix timefunction initialising for "+str(params["timefunctions"]))
        for f in params["timefunctions"]:
            logging.info(str(f))
            name = list(f.keys())[0]
            tf = importer.get_class("timefunction", name)(engine, device, f[name])
            self.mix_timefunctions.append(tf)

        self.operators = {
            "add" : self.operator_add,
            "and" : self.operator_and,
            "mul" : self.operator_mul
        }

        self.initial_state = {
            "add" : 0.0,
            "and" : 1.0,
            "mul" : 1.0
        }

    def state(self, t=None, t_relative=False):
        """Returns state of all child timefunctions, with operator performed on them"""
        r = self.initial_state[self.mix_operator]
        for tf in self.mix_timefunctions:
            r = self.operators[self.mix_operator](r, tf.state(t,t_relative))
        return r
    
    def next_change(self, t=None):
        """Return a future time when the next event will happen"""
        earliest = None
        for tf in self.mix_timefunctions:
            n = tf.next_change(t)
            if (earliest == None) or (n < earliest):
                earliest = n
        return earliest

    def period(self):
        """Least common multiple of all the periods. Eat my shorts."""
        periods = [tf.period() for tf in self.mix_timefunctions]
        return LCMM(periods)

    # Operators

    def operator_add(self, A, B):
        return A + B

    def operator_and(self, A, B):
        return A and B

    def operator_mul(self, A, B):
        return 0.5 + 2 * (float(A-0.5) * float(B-0.5))
