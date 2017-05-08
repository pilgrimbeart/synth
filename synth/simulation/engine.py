# abc for a simulation engine.
from abc import ABCMeta, abstractmethod

class Engine(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def start_event_loop(self):
        pass

    @abstractmethod
    def register_event_at(self, event, index):
        pass

    @abstractmethod
    def register_event_in(self, event, delta):
        pass

# create

# add event
# add event at time
# add event at delta
# run events
# has evemts
# pause
# stop
# status
