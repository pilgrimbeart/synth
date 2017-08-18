from device import Device
"""A basic device implementation"""
import random
import logging

class Basic(Device):
    deviceNumber = 0
    def __init__(self, time, engine, updateCallback, params):
        self.engine = engine
        self.updateCallback = updateCallback
        self.properties = {}
        self.properties["$id"] = "-".join([format(random.randrange(0,255),'02x') for i in range(6)])  # A 6-byte MAC address 01-23-45-67-89-ab
        self.properties["is_demo_device"] = True
        self.properties["label"] = "Thing "+str(Basic.deviceNumber)
        self.commsOK = True
        self.doComms(self.properties) # Communicate ALL properties on boot
        Basic.deviceNumber = Basic.deviceNumber + 1
        
    def externalEvent(self, eventName, arg):
        logging.info("Received external event "+eventName+" for device "+str(self.properties["$id"]))

##      TODO: Reinstate this functionality
##        # All other commands require device to be functional!
##        if self.getProperty("battery") <= 0:
##            logString("...ignored because battery flat")
##            return
##        if not self.commsOK:
##            logString("...ignored because comms down")
##            return

    def tickProductUsage(self, _):
        if self.propertyAbsent("battery") or self.getProperty("battery") > 0:
            self.setProperty("buttonPress", 1)
            t = timewave.nextUsageTime(self.engine.get_now(), ["Mon","Tue","Wed","Thu","Fri"], "06:00-09:00")
            self.engine.register_event_at(t, self.tickProductUsage, self)

    def setCommsReliability(self, upDownPeriod=1*60*60*24, reliability=1.0):
        self.commsUpDownPeriod = upDownPeriod
        self.commsReliability = reliability
        self.engine.register_event_in(0, self.tickCommsUpDown, self) # Immediately

    def getCommsOK(self):
        return self.commsOK
    
    def setCommsOK(self, flag):
        self.commsOK = flag
        
    def doComms(self, properties):
        t = self.engine.get_now()
        if self.commsOK:
            if self.updateCallback:
                if not "$ts" in properties: # Ensure there's a timestamp
                    properties["$ts"] = t
                self.updateCallback(self.properties["$id"], t, properties)
            else:
                logging.warning("No callback installed to update device properties")

    def getProperty(self, propName):
        return self.properties[propName]

    def propertyExists(self, propName):
        return propName in self.properties
    
    def propertyAbsent(self, propName):
        return not self.propertyExists(propName)
    
    def setProperty(self, propName, value):
        """Set device property and transmit an update"""
        newProps = { propName : value, "$id" : self.properties["$id"], "$ts" : self.engine.get_now() }
        self.properties.update(newProps)
        self.doComms(newProps)

    def setProperties(self, newProps):
        newProps.update({ "$id" : self.properties["$id"], "$ts" : self.engine.get_now() })  # Force ID and timestamp to be correct
        self.properties.update(newProps)
        self.doComms(newProps)

