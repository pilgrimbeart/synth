"""Combine timefunctions according to a given operator"""

from timefunction import Timefunction
from common import importer
from common.ordinal import LCMM

class Mix(Timefunction):
    """Combine timefunctions according to a given operator"""
    def __init__(self, engine, params):
        self.engine = engine
        self.mix_operator = params["operator"]
        self.mix_timefunctions = []
        for f in params["timefunctions"]:
            tf = importer.get_class("timefunction", f.keys()[0])(engine, f[f.keys()[0]])
            self.mix_timefunctions.append(tf)

        self.operators = {
            "and" : self.operator_and,
            "mul" : self.operator_mul
        }

        self.initial_state = {
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

    def operator_and(self, A, B):
        return A and B

    def operator_mul(self, A, B):
        return 0.5 + 2 * (float(A-0.5) * float(B-0.5))
