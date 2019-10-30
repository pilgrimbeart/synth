"""
lora_device
=====
Simulates a LoraWAN device (e.g. from The Things Network)

Configurable parameters::

    {
    }

Device properties created::

    {
    }

"""
import random
import logging
import time

from device import Device
import device_factory

MINUTES = 60
HOURS = MINUTES * 60
DAYS = HOURS * 24

NETWORK_INTERVAL = 15 * MINUTES

class Lora_device(Device):
    node_count = 0
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.set_id("node " +  str(Lora_device.node_count))
        Lora_device.node_count += 1
        super(Lora_device,self).__init__(instance_name, time, engine, update_callback, context, params)

        # self.sensor_type = params["disruptive"].get("sensor_type", None)
        self.set_property("metadata.type", "device")
        gw = self.closest_gateway()
        if gw:
            gw_props = gw.get_properties()
            self.set_properties( {
                "metadata.gateway.gtw_id" : gw_props["$id"],
                "metadata.gateway.latitude" : gw_props["latitude"],
                "metadata.gateway.longitude" : gw_props["longitude"]
                } )
        self.engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)
    
    def comms_ok(self):
        return super(Lora_device, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Lora_device,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Lora_device,self).close()

    # Private methods
    def closest_gateway(self):
        my_lat, my_lon = self.get_property("latitude"), self.get_property("longitude")
        closest = None
        closest_distance = 1e99
        for device in device_factory.get_devices_by_property("metadata.type", "gateway"):
            lat, lon = device.get_property("latitude"), device.get_property("longitude")
            dist = (my_lat - lat) * (my_lat - lat) + (my_lon - lon) * (my_lon - lon)    # Don't bother to sqrt. This will FAIL where lon wraps around from -180 to 180.
            if dist < closest_distance:
                closest = device
                closest_distance = dist
        return closest

    def tick_network(self, _):
        self.set_properties({}) # Just send a heartbeat with no data
        self.engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)


