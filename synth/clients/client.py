# abc for a client.
from abc import ABCMeta, abstractmethod

class Client:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_device(self, device):
        pass

# constructor
# delete
# update device
