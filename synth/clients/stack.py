from synth.clients.client import Client
from synth.common import importer

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stack(Client):
    @staticmethod
    def __build_client(conf):
        name = conf.get('type', 'console')
        cls = importer.get_class('client', name)
        return cls(conf)

    def __init__(self, confs):
        client_confs = confs.get('clients', [])
        logger.info("Adding clients as stack {confs}".format(confs=client_confs))
        self.clients = map(Stack.__build_client, client_confs)

    def add_device(self, device_id, time, properties):
        for client in self.clients:
            client.add_device(device_id, time, properties)

    def update_device(self, device_id, time, properties):
        for client in self.clients:
            client.update_device(device_id, time, properties)
