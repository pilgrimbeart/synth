import importlib
import logging

from clients.client import Client
from devices.device import Device
from engines.engine import Engine
from timefunctions.timefunction import Timefunction
from models.model import Model

modules = {}
families = {
        'engine': Engine,
        'client': Client,
        'device': Device,
        'timefunction': Timefunction,
        'model' : Model}
root = 'synth'


def __get_module(family, name):
    module_name = '.' + name
    package_name = "{family}s".format(family=family)
    full_name = package_name + module_name
    if full_name not in modules:
        logging.info("Loading "+str(full_name))
        mod = importlib.import_module(module_name, package_name)
        modules[full_name] = mod
    return modules[full_name]


def get_class(family, name):
    mod = __get_module(family, name)
    class_name = name.split('.')[-1].capitalize()
    cls = getattr(mod, class_name)
    assert issubclass(cls, families[family])
    return cls
