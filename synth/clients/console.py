from synth.clients.client import Client

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Console(Client):

    def __init__(self, conf):
        self.name = conf.get('name', 'console')
        logger.info("[{name}]:Started console client.".format(name = self.name))

    def add_device(self, device):
        print("[{name}]:Added new device: {state}".format(
            name = self.name,
            state = device.get_state())
        )

    def update_device(self, device):
        print("[{name}]:Updated device: {state}".format(
            name = self.name,
            state = device.get_state())
        )
