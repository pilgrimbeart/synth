# abc for a device
from abc import ABCMeta, abstractmethod


class Device(object):
    __metaclass__ = ABCMeta

    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self, time, engine, updateCallback, params):
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def externalEvent(self, eventName, arg):
        pass
