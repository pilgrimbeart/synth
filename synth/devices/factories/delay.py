import pendulum
import logging

from synth.common import importer
from synth.common.conftime import get_interval
from synth.devices.device import Device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Delay(Device):
    def __build_create(self, conf):
        this_conf = dict.copy(conf)
        return lambda time: self.create(dict.copy(this_conf), time)

    def __init__(self, conf, engine, client):
        super(Delay, self).__init__(conf, engine, client)
        self.engine = engine
        self.client = client

        delay = get_interval(conf, 'delay', pendulum.interval())
        device_conf = conf['device']
        logger.info("Delaying creation of device {conf} until {delay}.".format(conf=conf, delay=delay))
        self.engine.register_event_in(self.__build_create(device_conf), delay)

    def create(self, conf, time):
        logger.info("@{time}: Delayed creation of new device: {conf}".format(conf=conf, time=time))
        name = conf['type']
        cls = importer.get_class('device', name)
        cls(conf, self.engine, self.client)
