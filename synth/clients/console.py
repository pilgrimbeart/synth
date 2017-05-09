from synth.clients.client import Client

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Console(Client):
    def __init__(self, conf):
        self.name = conf.get('name', 'console')
        logger.info("[{name}]:Started console client.".format(name=self.name))

    def add_device(self, device_id, time, properties):
        print("[{name}]:{time}:{id} > Added new device: {properties}".format(
            name=self.name,
            time=time,
            id=device_id,
            properties=properties,
        ))

    def update_device(self, device_id, time, properties):
        print("[{name}]:{time}:{id} > Updated device: {properties}".format(
            name=self.name,
            time=time,
            id=device_id,
            properties=properties,
        ))
