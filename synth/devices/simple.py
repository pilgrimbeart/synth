from synth.devices.device import Device

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Simple(Device):

    @staticmethod
    def build_estate(estate_configuration, engine, client_stack):
        for device_configuration in estate_configuration:
            Simple(device_configuration, engine, client_stack)

    def __init__(self, conf, engine, client):
        self.engine = engine
        self.client = client

        self.value = conf['initial']
        self.delay = conf['delay']
        self.increment = conf['increment']
        self.interval = conf['interval']

        logger.info("Created new device with {initial} + {increment} @ {delay} / {interval}".format(
            initial = self.value, increment = self.increment, interval = self.interval, delay = self.delay)
        )
