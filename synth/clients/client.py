# abc for a client.
from abc import ABCMeta, abstractmethod

class Client:
    @abstractmethod
    def foo(self):
        pass

    @abstractmethod
    def bar(self):
        pass