"""
lora_gateway
=====
Simulates a LoraWAN gateway (e.g. from The Things Network)

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

class Lora_gateway(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.set_id("eui-" +  "".join(random.choice("0123456789abcdef") for i in range(16)))
        super(Lora_gateway,self).__init__(instance_name, time, engine, update_callback, context, params)
        # self.sensor_type = params["disruptive"].get("sensor_type", None)
        self.set_property("metadata.type", "gateway")
        self.engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)
    
    def comms_ok(self):
        return super(Lora_gateway, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Lora_gateway,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Lora_gateway,self).close()

    # Private methods
    def tick_network(self, _):
        self.set_properties({}) # Just send a heartbeat with no data
        self.engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)


