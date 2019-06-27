# abc for a device
from abc import ABCMeta, abstractmethod

class Model(object):
    __metaclass__ = ABCMeta

    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self):
        pass

