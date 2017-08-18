from device import Device
import random
import isodate
import logging

class Battery(Device):
    def __init__(self, time, engine, updateCallback, params):
        """Set battery life with a normal distribution which won't exceed 2 standard deviations."""
        super(Battery,self).__init__(time, engine, updateCallback, params)
        mu = isodate.parse_duration(params["battery"].get("life_mu", "PT5M")).total_seconds()
        sigma = isodate.parse_duration(params["battery"].get("life_sigma", "PT0S")).total_seconds()
        life = random.normalvariate(mu, sigma)
        life = min(life, mu+2*sigma)
        life = max(life, mu-2*sigma)
        self.battery_life = life
        self.battery_autoreplace = params["battery"].get("autoreplace", False)

        self.properties["battery"] = 100

        self.engine.register_event_in(self.battery_life/100.0, self.tickBatteryDecay, self)

    def externalEvent(self, eventName, arg):
        super(Battery,self).externalEvent(eventName, arg)
        if eventName=="replaceBattery":
            logging.info("Replacing battery on device "+self.properties["$id"])
            self.setProperty("battery", 100)
            self.engine.register_event_in(self.battery_life/100.0, self.tickBatteryDecay, self)

    # Private methods
    
    def tickBatteryDecay(self,_):
        v = self.getProperty("battery")
        if v > 0:
            self.setProperty("battery", v-1)
            self.engine.register_event_in(self.battery_life / 100.0, self.tickBatteryDecay, self)
        else:
            if self.battery_autoreplace:
                logging.info("Auto-replacing battery on device "+self.properties["$id"])
                self.setProperty("battery",100)
                self.engine.register_event_in(self.batteryLife / 100.0, self.tickBatteryDecay, self)
            # otherwise we stop ticking
        
