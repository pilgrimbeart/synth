from synth.devices.device import Device
from synth.common.conftime import get_interval

import logging

logger = logging.getLogger(__name__)


class Simple(Device):
    def __init__(self, conf, engine, client):
        super(Simple, self).__init__(conf, engine, client)
        self.engine = engine
        self.client = client

        self.value = conf['initial']
        self.increment = conf['increment']
        self.interval = get_interval(conf, 'interval', None)
        self.id = conf['id']
        logger.info("Created new device {id} with {initial} + {increment} @ {interval}".format(
            id=self.id,
            initial=self.value,
            increment=self.increment,
            interval=self.interval,
        ))

        self.client.add_device(self.id, engine.get_now(), {'value': self.value})
        self.engine.register_event_in(self.tick, self.interval, None, self)

    def get_state(self):
        return {'id': self.id, 'value': self.value}

    def tick(self, time):
        self.value += self.increment
        logger.info("@{time}: Ticking device {id} to {value}".format(time=time, id=self.id, value=self.value))
        self.client.update_device(self.id, time, {'value': self.value})
        self.engine.register_event_in(self.tick, self.interval, None, self)
