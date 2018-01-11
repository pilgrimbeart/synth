import logging
import math
import random  # TODO: replace with safe random.
import pendulum

from synth.devices.device import Device
from synth.clients.client import Client

logger = logging.getLogger(__name__)


class Mobile(Device, Client):
    """ Reliably unreliable communication emulator. """

    # Device
    def __init__(self, conf, engine, client):
        self.engine = engine
        self.client = client

        self.mean_up_down_period = pendulum.interval(days=1)
        if 'rssi' in conf and 'reliabilitySchedule' in conf:
            self.use_rssi = True
            # use a normalised radio signal strength heavily skewed to 'strong'.
            strong_rssi = -50.0
            weak_rssi = -120.0
            normalised_rssi = (conf['rssi'] - strong_rssi) / (weak_rssi - strong_rssi)
            self.radio_strength = 1.0 - math.pow((1.0 - normalised_rssi), 4)
        else:
            self.use_rssi = False
            self.reliability = conf.get('reliability', 1.0)

        self.is_connected = True
        self.set_connected(engine.get_now())

    # Client
    def add_device(self, device_id, time, properties):
        self.client.add_device(self, device_id, time, properties)

    def update_device(self, device_id, time, properties):
        if self.is_connected:
            self.client.update_device(self, device_id, time, properties)


    # Device
    def set_connected(self, time):
        if self.use_rssi:
            self.is_connected = True
            current_reliability = 1.0 # TODO: synth.simulation.helpers.timewave.interp(self.commsReliability, rel_time)
            self.is_connected = (current_reliability * self.radio_strength) > random.random()
        else:
            # simple probability.
            self.is_connected = self.reliability > random.random()

        next = min(
            random.expovariate(1 / self.mean_up_down_period.total_seconds()),
            self.mean_up_down_period.total_seconds() * 100
        )
        self.engine.register_event_in(self.set_connected, pendulum.interval(seconds=next), None, self)
