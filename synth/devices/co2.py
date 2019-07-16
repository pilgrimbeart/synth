"""
co2
=====
Simulates co2 levels (driven by local occupancy)

Configurable parameters::

    {
    }

Device properties created::

    {
        "co2_ppm"
    }


    Good summary of limits for CO2 here: https://www.engineeringtoolbox.com/co2-comfort-level-d_1024.html

"""
import random
import logging
import time

from device import Device

CO2_POLL_INTERVAL_S = 60 * 15

MIN_CO2_LEVEL_PPM = 400     # Should be based on year!
MAX_CO2_LEVEL_PPM = 5000

COUPLING = 0.1  # The bigger this is, the quicker CO2 rises and falls

def sensor_noise(n):
    noise_level = MIN_CO2_LEVEL_PPM / 10.0
    return int(n - noise_level/2 + random.random() * noise_level)

class Co2(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Co2,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.co2_ppm = sensor_noise(MIN_CO2_LEVEL_PPM)
        self.engine.register_event_in(CO2_POLL_INTERVAL_S, self.tick_co2, self, self)

    def comms_ok(self):
        return super(Co2,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Co2,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Co2,self).close()

    # Private methods
    def measure_occupancy(self):
        tot=0
        occ=0
        for peer in self.model.get_peers(self):
            if peer.get_property("device_type", None) == "occupancy":
                tot += 1
                if peer.get_property("occupied"):
                    occ += 1
        # logging.info("occupancy "+str(occ)+"/"+str(tot))
        if tot == 0:
            return 0.0
        return float(occ)/tot

    def tick_co2(self, _):
        occupancy_fraction = self.measure_occupancy()
        # logging.info("occupancy_fraction for device "+str(self.get_property("$id"))+" is "+str(occupancy_fraction))

        target = MIN_CO2_LEVEL_PPM + (MAX_CO2_LEVEL_PPM - MIN_CO2_LEVEL_PPM) * occupancy_fraction
        self.co2_ppm = (self.co2_ppm * (1-COUPLING)) + (target * COUPLING)
        self.set_property("co2_ppm", sensor_noise(self.co2_ppm))
        self.engine.register_event_in(CO2_POLL_INTERVAL_S, self.tick_co2, self, self)

