import logging

from synth.devices.device import Device
from synth.common import importer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Generate(Device):
    @staticmethod
    def __set_nested_key(conf, key, value):
        nested_conf = conf
        for nested_key in key.split('.')[:-1]:
            if nested_key not in nested_conf:
                nested_conf[nested_key] = {}
            nested_conf = nested_conf[nested_key]
        nested_conf[key.split('.')[-1]] = value

    def __init__(self, conf, engine, client):
        super(Generate, self).__init__(conf, engine, client)

        template = conf['template']
        count = conf['count']
        id_scheme = conf.get('idScheme', '{id}')
        id_key = conf.get('idKey', 'id')

        for id in range(1, count + 1):
            device_id = id_scheme.format(id=id)
            device_conf = dict.copy(template)
            Generate.__set_nested_key(device_conf, id_key, device_id)

            logger.info("Generating device {device_id} as {device_conf}".format(
                device_id=device_id,
                device_conf=device_conf,
            ))
            importer.get_class('device', device_conf['type'])(device_conf, engine, client)
