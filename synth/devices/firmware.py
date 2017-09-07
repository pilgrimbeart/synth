from device import Device
import random
import logging

class Firmware(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        super(Firmware,self).__init__(instance_name, time, engine, update_callback, params)
        fw = random.choice(["0.51","0.52","0.6","0.6","0.6","0.7","0.7","0.7","0.7"])
        self.set_properties({'factoryFirmware' : fw, 'firmware' : fw } )

    def comms_ok(self):
        return super(Firmware,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Firmware,self).external_event(event_name, arg)
        if event_name=="upgradeFirmware":
            logging.info("Upgrading firmware on device "+self.properties["$id"]+" to "+str(arg))
            self.set_property("firmware", arg)
        if event_name=="factoryReset":
            logging.info("Factory-resetting firmware on device "+self.properties["$id"])
            self.set_property("firmware", self.get_property("factoryFirmware"))
