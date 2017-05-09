# abc for a simulation engine.
from abc import ABCMeta, abstractmethod


class Engine(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def start_event_loop(self):
        pass

    @abstractmethod
    def register_event_at(self, event, time):
        pass

    @abstractmethod
    def register_event_in(self, event, interval):
        pass

    @abstractmethod
    def get_now(self):
        pass
