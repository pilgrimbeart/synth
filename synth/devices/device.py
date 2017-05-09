# abc for a device
from abc import ABCMeta, abstractmethod


class Device(object):
    __metaclass__ = ABCMeta

    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self, conf, engine, client):
        pass

    @abstractmethod
    def get_state(self):
        pass
