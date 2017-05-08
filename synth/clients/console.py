from synth.clients.client import Client

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Console(Client):

    def __init__(self, conf):
        logger.info("Started console client.")

    def add_device(self, device):
        logger.info("Added new device: {state}".format(state = device.get_state()))

    def update_device(self, device):
        logger.info("Updated device: {state}".format(state = device.get_state()))
