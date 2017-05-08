# abc for a simulation engine.
from abc import ABCMeta, abstractmethod

class Engine(object):
    @abstractmethod
    def start_event_loop(self):
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
