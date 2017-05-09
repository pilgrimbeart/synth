# abc for a client.
from abc import ABCMeta, abstractmethod


class Client:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_device(self, id, time, properties):
        pass

    @abstractmethod
    def update_device(self, id, time, properties):
        pass

# constructor
# delete
# update device
