import logging

from synth.common import importer
from synth.devices.device import Device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Delay(Device):
    def __build_create(self, conf):
        return lambda: self.create(conf)

    def __init__(self, conf, engine, client):
        super(Delay, self).__init__(conf, engine, client)
        self.engine = engine
        self.client = client

        for device in conf.get('devices', []):
            delay = device.get('delay', 0)
            device_conf = device['device']
            logger.info("Delaying creation of device until {delay}.".format(delay=delay))
            self.engine.register_event_at(self.__build_create(device_conf), delay)

    def create(self, conf):
        logger.info("Delayed creation of new device: {conf}".format(conf=conf))
        name = conf['type']
        cls = importer.get_class('device', name)
        cls(conf, self.engine, self.client)

    def get_state(self):
        pass
