import logging
import random  # TODO: replace with safe random.
import pendulum

from synth.common.ordinal import as_ordinal
from synth.common.conftime import get_interval
from synth.devices.device import Device
from synth.devices.blb_helpers.solar_math import sun_bright

logger = logging.getLogger(__name__)


class Blb(Device):
    """ Battery (powered) light (measuring) button. """

    def __init__(self, conf, engine, client):
        super(Device, self).__init__()
        self.engine = engine
        self.client = client

        # generate identifiers
        self.id = "-".join([format(random.randrange(0, 255), '02x') for i in range(6)]) # i.e. a MAC address
        self.is_demo_device = conf.get('isDemoDevice', True) # identifier for later deletion.
        self.label = conf.get('name', 'Thing ' + self.id)

        self.firmware = random.choice(["0.51","0.52","0.6","0.6","0.6","0.7","0.7","0.7","0.7"])
        self.factory_firmware = self.firmware

        self.operator = random.choice(["O2","O2","O2","EE","EE","EE","EE","EE"])

        # setup battery
        self.battery = 100
        if 'batteryLifeMu' in conf and 'batteryLifeSigma' in conf:
            battery_life_mu = get_interval(conf, 'batteryLifeMu', None).total_seconds()
            battery_life_sigma = get_interval(conf, 'batteryLifeSigma', None).total_seconds()
            battery_life_min = battery_life_mu - (2 * battery_life_sigma)
            battery_life_max = battery_life_mu + (2 * battery_life_sigma)
            battery_life = random.normalvariate(battery_life_mu, battery_life_sigma)
            # noinspection PyArgumentList
            self.battery_life = pendulum.interval(seconds=max(min(battery_life, battery_life_min), battery_life_max))
        else:
            # noinspection PyArgumentList
            self.battery_life = get_interval(conf, 'batteryLife', pendulum.interval(minutes=5))
        self.battery_auto_replace = conf.get('batteryAutoReplace', False)
        self.engine.register_event_in(self.battery_decay, self.battery_life / 100)

        # setup button press counter
        self.button_press_count = 0
        self.engine.register_event_in(self.press_button, pendulum.interval())

        # setup light measurement
        self.longitude = conf.get('longitude', 0)
        self.latitude = conf.get('latitude', 0)
        self.light = 0.0
        # noinspection PyArgumentList
        self.engine.register_event_in(self.measure_light, pendulum.interval(hours=12))

        self.client.add_device(self.id, engine.get_now(), {
            'battery': self.battery,
            'longitude': self.longitude,
            'latitude': self.latitude,
        })

    def press_button(self, time):
        if self.battery > 0:
            self.button_press_count += 1
            self.client.update_device(self.id, time, {'buttonPress': self.button_press_count})
            # noinspection PyArgumentList
            next_press_interval = pendulum.interval(hours=1)  # TODO: timewave?
            # timewave
            # .next_usage_time
            # synth.simulation.sim.get_time(),
            # ["Mon", "Tue", "Wed", "Thu", "Fri"], "06:00-09:00"
            logger.info("{id}: Pressed button for the {nth} time.".format(
                id=self.id,
                nth=as_ordinal(self.button_press_count),
            ))
            self.engine.register_event_in(self.press_button, next_press_interval)

    def battery_decay(self, time):
        self.battery -= 1

        if self.battery <= 0 and self.battery_auto_replace:
            logger.info("{id}: Auto-replacing battery.".format(id=self.id))
            self.battery = 100

        logger.info("{id}: Battery decayed to {battery}".format(id=self.id, battery=self.battery))
        self.client.update_device(self.id, time, {'battery': self.battery})

        if self.battery > 0:
            self.engine.register_event_in(self.battery_decay, self.battery_life / 100)

    def measure_light(self, time):
        if self.battery > 0:
            self.light = sun_bright(time.int_timestamp, (self.longitude, self.latitude))
            # sun_bright(synth.simulation.sim.get_time(),
            #  (float(Device.get_property(self, "longitude")),
            #   float(Device.get_property(self, "latitude")))
            #  ))
            self.client.update_device(self.id, time, {'light': self.light})
            # noinspection PyArgumentList
            self.engine.register_event_in(self.measure_light, pendulum.interval(hours=1))
