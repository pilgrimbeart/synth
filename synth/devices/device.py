# abc for a device
from abc import ABCMeta, abstractmethod

class Device(object):
    __metaclass__ = ABCMeta

# constructor
# serialiser
# action (webhook)
# init

# needs sim injected.
# needs client injected.

    @classmethod
    def build_estate(cls, estate_configuration, engine, client_stack):
        pass

    @abstractmethod
    def __init__(self, conf, engine, client):
        pass

    @abstractmethod
    def get_state(self):
        pass
