# abc for a device
from abc import ABCMeta, abstractmethod


class Device(object):
    __metaclass__ = ABCMeta

    @classmethod
    def build_estate(cls, estate_configuration, engine, client_stack):
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self, conf, engine, client):
        pass

    @abstractmethod
    def get_state(self):
        pass
