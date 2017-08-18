from device import Device
import random

class Firmware(Device):
    def __init__(self, time, engine, updateCallback, params):
        super(Firmware,self).__init__(time, engine, updateCallback, params)
        print "Firmware __init__"
        fw = random.choice(["0.51","0.52","0.6","0.6","0.6","0.7","0.7","0.7","0.7"])
        self.setProperties({'factoryFirmware' : fw, 'firmware' : fw } )

    def externalEvent(self, eventName, arg):
        super(Firmware,self).externalEvent(eventName, arg)
        if eventName=="upgradeFirmware":
            self.setProperty("firmware", arg)
        if eventName=="factoryReset":
            self.setProperty("firmware", self.getProperty("factoryFirmware"))
