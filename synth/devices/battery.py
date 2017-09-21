from device import Device
import random
import isodate
import logging

class Battery(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        """Set battery life with a normal distribution which won't exceed 2 standard deviations."""
        super(Battery,self).__init__(instance_name, time, engine, update_callback, params)
        x = params["battery"]["life_mu"]
        mu = isodate.parse_duration(params["battery"].get("life_mu", "PT5M")).total_seconds()
        sigma = isodate.parse_duration(params["battery"].get("life_sigma", "PT0S")).total_seconds()
        life = random.normalvariate(mu, sigma)
        life = min(life, mu+2*sigma)
        life = max(life, mu-2*sigma)
        life = max(life, 1.0) # Sensible minimum. A battery life of 0 causes auto-replace to blow up.
        self.battery_life = life
        self.battery_autoreplace = params["battery"].get("autoreplace", False)

        self.properties["battery"] = 100

        self.engine.register_event_in(self.battery_life/100.0, self.tick_battery_decay, self)

    def comms_ok(self):
        return super(Battery,self).comms_ok() and (self.properties.get("battery",100) > 0)

    def external_event(self, event_name, arg):
        super(Battery,self).external_event(event_name, arg)
        if eventName=="replaceBattery":
            logging.info("Replacing battery on device "+self.properties["$id"])
            self.set_property("battery", 100)
            self.engine.register_event_in(self.battery_life/100.0, self.tick_battery_decay, self)

    def close(self, err_str):
        super(Battery,self).close(err_str)
        
    # Private methods
    
    def tick_battery_decay(self,_):
        v = self.get_property("battery")
        if v > 0:
            self.set_property("battery", v-1)
            self.engine.register_event_in(self.battery_life / 100.0, self.tick_battery_decay, self)
        else:
            if self.battery_autoreplace:
                logging.info("Auto-replacing battery on device "+self.properties["$id"])
                self.set_property("battery",100)
                self.engine.register_event_in(self.battery_life / 100.0, self.tick_battery_decay, self)
            # otherwise we stop ticking
        
