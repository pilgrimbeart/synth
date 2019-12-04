"""
weather
=====
Captures real weather data from Dark Sky.
Requires that devices have a (latitude, longitude)

Configurable parameters::

    {
    }

Device properties created::

    {
        <TODO>
    }

"""

from .device import Device
from helpers import dark_sky
import logging

MEASUREMENT_INTERVAL_S = 60*60

class Weather(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Weather,self).__init__(instance_name, time, engine, update_callback, context, params)
        if not self.property_exists("device_type"):
            self.set_property("device_type", "weather")
        self.occupied_bodge = params["weather"].get("occupied_bodge", False)
        if self.occupied_bodge:
            self.set_property("occupied", False)    # !!!!!! TEMP BODGE TO OVERCOME CLUSTERING PROBLEM
        engine.register_event_in(0, self.tick_weather, self, self)

    def comms_ok(self):
        return super(Weather,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Weather,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Weather,self).close()

    # Private methods
    def tick_weather(self, _):
        lat = self.get_property("latitude")
        lon = self.get_property("longitude")
        props = dark_sky.get_weather(lat, lon, int(self.engine.get_now()))
        self.set_properties(props)
        if self.occupied_bodge:
            self.set_property("occupied", not self.get_property("occupied"))
        self.engine.register_event_in(MEASUREMENT_INTERVAL_S, self.tick_weather, self, self)

