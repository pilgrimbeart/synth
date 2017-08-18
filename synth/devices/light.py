from device import Device
from solar import solar
import random

class Light(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Light,self).__init__(time, engine, updateCallback, params)
        engine.register_event_in(0, self.tickLight, self)

    def externalEvent(self, eventName, arg):
        super(Light,self).externalEvent(eventName, arg)
        pass

    # Private methods
    def tickLight(self):
        lon = float(self.properties.get("longitude", 0.0))
        lat = float(self.properties.get("latitude", 0.0))
        light = solar.sunBright(self.engine.get_now(), lon, lat)
        self.setProperty("light", light)
        engine.register_event_in(60*60, self.tickLight, self)
