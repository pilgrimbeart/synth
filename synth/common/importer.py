import importlib
import logging

from clients.client import Client
from devices.device import Device
from engines.engine import Engine

logger = logging.getLogger(__name__)

modules = {}
families = {'engine': Engine, 'client': Client, 'device': Device}
root = 'synth'


def __get_module(family, name):
    module_name = '.' + name
    package_name = "{family}s".format(family=family)
    full_name = package_name + module_name
    logging.info("Loading "+package_name+module_name)
    if full_name not in modules:
        mod = importlib.import_module(module_name, package_name)
        modules[full_name] = mod
        logger.info("Loaded {type} module: {name}".format(type=name, name=full_name))
    return modules[full_name]


def get_class(family, name):
    mod = __get_module(family, name)
    class_name = name.split('.')[-1].capitalize()
    cls = getattr(mod, class_name)
    assert issubclass(cls, families[family])
    return cls
