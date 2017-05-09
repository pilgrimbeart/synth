# abc for a client.
from abc import ABCMeta, abstractmethod

class Client:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_device(self, device):
        pass

    @abstractmethod
    def update_device(self, device):
        pass

    @staticmethod
    def build(cls, conf):
        type = conf.get('type', 'console')


# constructor
# delete
# update device
