# abc for a device
from abc import ABCMeta, abstractmethod

class Device:
    @abstractmethod
    def add_device(self):
        pass


# constructor
# serialiser
# action (webhook)
# init

# needs sim injected.
# needs client injected.


    @classmethod
    def build_estate(cls, estate_configuration, engine, client_stack):
        pass