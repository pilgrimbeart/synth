# abc for a simulation engine.
from abc import ABCMeta, abstractmethod


class Engine(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, params, cb):
        """If defined, <cb> callback will be called when (if) simulator moves from historical to real-time.
           This callback must NOT create new events, or deadlock will occur"""
        pass

## This now split into events_to_come() and next_event()
## so that we retain control at the top level
##    @abstractmethod
##    def start_event_loop(self):
##        pass

    @abstractmethod
    def events_to_come(self):
        """Return True if there are any future events to simulate"""
        pass

    @abstractmethod
    def next_event(self):
        """Execute next event(s)

       Call this repeatedly from top loop, while events_to_come()"""
        pass

    @abstractmethod
    def register_event_at(self, time, event, arg=None):
        """Schedule an event (callback) at a given time. <arg> will be passed to callback."""
        pass

    @abstractmethod
    def register_events_at(self, times, func, arg=None):
        """Schedule multiple events at times[]"""
        pass

    @abstractmethod
    def register_event_in(self, interval, event):
        """Schedule an event (callback) after a given interval from current sim time"""
        pass

    @abstractmethod
    def set_now(self):
        """Set current simulation time"""
        pass

    @abstractmethod
    def set_now_str(self, is_start_time):
        """Set current simulation time (passed as an ISO8601 string)"""
        pass

    @abstractmethod
    def set_start_time_str(self):
        """Set simulation start time (passed as an ISO8601 string)"""
        pass

    @abstractmethod
    def set_end_time_str(self):
        """Set simulation end time (passed as an ISO8601 string)"""
        pass

    @abstractmethod
    def get_start_time(self):
        """Get simulation start time"""
        pass

    @abstractmethod
    def get_now(self):
        """Return current simulation time"""
        pass

    @abstractmethod
    def get_now_str(self):
        """Return current simulation time as an ISO8601 string"""
        pass

    @abstractmethod
    def get_now_no_lock(self):
        """Return current simulation time (no danger of deadlock, may very occasionally be corrupted)"""
        pass

    @abstractmethod
    def get_now_1000(self):
        """Return current simulation time in epoch-ms"""
        pass

