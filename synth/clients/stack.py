from synth.clients.client import Client

from synth.clients.console import Console

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Stack(Client):

    def __init__(self, confs):
        logger.info("Adding clients as stack {confs}".format(confs = confs))
        self.clients = map(lambda c: Console(c), confs)

    def add_device(self, device):
        for client in self.clients:
            client.add_device(device)

    def update_device(self, device):
        for client in self.clients:
            client.update_device(device)
