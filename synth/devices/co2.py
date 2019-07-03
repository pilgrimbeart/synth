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
"""
import random
import logging
import time

from device import Device

CO2_POLL_INTERVAL_S = 60 * 15

MIN_CO2_LEVEL_PPM = 400     # Should be based on year!
INTOLERABLE_CO2_LEVEL_PPM = 1000
CO2_RISE_PER_HOUR = 400

CO2_CHANGE_PER_INTERVAL = CO2_RISE_PER_HOUR * (CO2_POLL_INTERVAL_S / (60.0*60))

def sensor_noise(n):
    return int(n - 10 + random.random() * 20)

class Co2(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Co2,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.set_property("device_type", "co2")
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

        if occupancy_fraction == 0.0:
            self.co2_ppm -= CO2_CHANGE_PER_INTERVAL
        else:
            self.co2_ppm += occupancy_fraction * CO2_CHANGE_PER_INTERVAL
        self.co2_ppm = max(self.co2_ppm, MIN_CO2_LEVEL_PPM)
        self.set_property("co2_ppm", sensor_noise(self.co2_ppm))
        self.engine.register_event_in(CO2_POLL_INTERVAL_S, self.tick_co2, self, self)

