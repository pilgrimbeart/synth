# abc for a simulation engine.
from abc import ABCMeta, abstractmethod

class Timefunction(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, engine, params):
        pass

    @abstractmethod
    def current_state(self):
        """Return state of timefunction at the current time"""
        pass

    @abstractmethod
    def next_change(self, time):
        """Return next time that state will change"""
        pass
