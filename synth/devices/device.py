# abc for a device
from abc import ABCMeta, abstractmethod


class Device(object):
    __metaclass__ = ABCMeta

    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self, instance_name, time, engine, update_callback, params):
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def comms_ok(self):
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def external_event(self, event_name, arg):
        pass

    # noinspection PyUnusedLocal
    @abstractmethod
    def close(self, err_str):
        pass
