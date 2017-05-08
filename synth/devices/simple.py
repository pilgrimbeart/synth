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
        self.id = conf['id']

        logger.info("Created new device {id} with {initial} + {increment} @ {delay} / {interval}".format(
            id = self.id,
            initial = self.value,
            increment = self.increment,
            interval = self.interval,
            delay = self.delay),
        )

        self.engine.register_event_at(self.create, self.delay)

    def get_state(self):
        return { 'id': self.id, 'value': self.value }

    def create(self):
        logger.info("Added device {id}".format(id = self.id))
        self.client.add_device(self)
        self.engine.register_event_in(self.tick, self.interval)

    def tick(self):
        self.value += self.increment
        logger.info("Ticking device {id} to {value}".format(id = self.id, value = self.value))
        self.client.update_device(self)
        self.engine.register_event_in(self.tick, self.interval)
