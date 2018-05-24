# abc for a simulation engine.
from abc import ABCMeta, abstractmethod

class Timefunction(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, engine, device, params):
        pass

    @abstractmethod
    def state(self, t=None):
        """Return state of timefunction at the given epoch-time <t>, or at current simulation time if no <t> is given"""
        pass

    @abstractmethod
    def next_change(self, t=None):
        """Return next time that state will change"""
        pass

    @abstractmethod
    def period(self):
        """Return period of timefunction in seconds"""
        pass
