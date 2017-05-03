#!/usr/bin/env python
#
# DEVICE
# A generic device class
# A global set of all known devices
# Some simple behaviours
#
# Copyright (c) 2017 DevicePilot Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import random, math
import sim
import timewave
from solar import solar
import datetime
import threading
import logging, traceback

devices = []

updateCallback = None
logfile = None
DEFAULT_BATTERY_LIFE_S = sim.minutes(5)   # For interactive process demo

GOOD_RSSI = -50.0
BAD_RSSI = -120.0

def init(updatecallback, logfileName):
    global updateCallback
    global logfile
    updateCallback = updatecallback
    logfile = open("../synth_logs/"+logfileName+".evt","at",0)    # Unbuffered
    logfile.write("*** New simulation starting at real time "+datetime.datetime.now().ctime()+"\n")

def numDevices():
    global devices
    n = len(devices)
    return n

def getDeviceByProperty(prop,value):
    global devices
    for d in devices:
        if prop in d.properties:
            if d.properties[prop]==value:
                return d
    return None

def logEntry(properties):
    logfile.write(sim.getTimeStr()+" ")
    for k in sorted(properties.keys()):
        s = str(k) + ","
        if isinstance(properties[k], basestring):
            try:
                s += properties[k].encode('ascii','ignore') # Python 2.x barfs if you try to write unicode into an ascii file
            except:
                s += "<unicode encoding error>"
        else:
            s += str(properties[k])
        s+= ","
        logfile.write(s) # Property might contain unicode
    logfile.write("\n")

def logString(s):
    logging.info(s)
    logfile.write(sim.getTimeStr()+" "+s+"\n")

def flush():
    logging.info("Ending device logging ("+str(len(devices))+" devices were emulated)")
    logfile.close()

def externalEvent(params):
    # Accept events from outside world
    # (these have already been synchronised via the event queue so we don't need to worry about thread-safety here)
    global devices
    body = params["body"]
    try:
        logging.info("external Event received: "+str(params))
        for d in devices:
            if d.properties["$id"] == body["deviceId"]:
                arg = None
                if "arg" in body:
                    arg = body["arg"]
                d.externalEvent(body["eventName"], arg)
                return
        e = "No such device "+str(deviceID)+" for incoming event "+str(eventName)
        logString(e)
    except Exception as e:
        logString("Error processing external event")
        logging.error("Error processing externalEvent: "+str(e))
        logging.error(traceback.format_exc())
        
class device():
    def __init__(self,props,autoTick=True): # <props> MUST include a "$id" field so we can de-duplicate
        global devices
        assert "$id" in props,"The $id property must be defined when creating a device"
        if getDeviceByProperty("$id",props["$id"]) != None:
            logging.error("FATAL: Attempt to create duplicate device "+str(props["$id"]))
            exit(-1)
        else:
            self.properties = props
            devices.append(self)
            self.commsReliability = 1.0 # Either a fraction, or a string containing a specification of the trajectory
            self.commsUpDownPeriod = sim.days(1)
            self.batteryLife = DEFAULT_BATTERY_LIFE_S
            self.batteryAutoreplace = False
            self.commsOK = True
            self.doComms(self.properties)
            if autoTick:
                self.startTicks()

    def startTicks(self):
        if self.propertyExists("battery"):
            sim.injectEventDelta(self.batteryLife / 100.0, self.tickBatteryDecay, self)
        sim.injectEventDelta(sim.hours(1), self.tickHourly, self)
        sim.injectEventDelta(0, self.tickProductUsage, self)    # Immediately

    def externalEvent(self, eventName, arg):
        s = "Processing external event "+eventName+" for device "+str(self.properties["$id"])
        logString(s)
        if eventName=="replaceBattery":
            self.setProperty("battery", 100)
            self.startTicks()

        # All other commands require device to be functional!
        if self.getProperty("battery") <= 0:
            logString("...ignored because battery flat")
            return
        if not self.commsOK:
            logString("...ignored because comms down")
            return
        
        if eventName=="upgradeFirmware":
            self.setProperty("firmware", arg)
        if eventName=="factoryReset":
            self.setProperty("firmware", self.getProperty("factoryFirmware"))

    def tickProductUsage(self, _):
        if self.propertyAbsent("battery") or self.getProperty("battery") > 0:
            self.setProperty("buttonPress", 1)
            t = timewave.nextUsageTime(sim.getTime(), ["Mon","Tue","Wed","Thu","Fri"], "06:00-09:00")
            sim.injectEvent(t, self.tickProductUsage, self)

    def setCommsReliability(self, upDownPeriod=sim.days(1), reliability=1.0):
        self.commsUpDownPeriod = upDownPeriod
        self.commsReliability = reliability
        sim.injectEventDelta(0, self.tickCommsUpDown, self) # Immediately

    def getCommsOK(self):
        return self.commsOK
    
    def setCommsOK(self, flag):
        self.commsOK = flag
        
    def setBatteryLife(self, mu, sigma, autoreplace=False):
        # Set battery life with a normal distribution which won't exceed 2 standard deviations
        life = random.normalvariate(mu, sigma)
        life = min(life, mu+2*sigma)
        life = max(life, mu-2*sigma)
        self.batteryLife = life
        self.batteryAutoreplace = autoreplace
        
    def tickCommsUpDown(self, _):
        if isinstance(self.commsReliability, (int,float)):   # Simple probability
            self.commsOK = self.commsReliability > random.random()
        else:   # Probability spec, i.e. varies with time
            relTime = sim.getTime() - sim.startTime
            prob = timewave.interp(self.commsReliability, relTime)
            if self.propertyExists("rssi"): # Now affect comms according to RSSI
                rssi = self.getProperty("rssi")
                radioGoodness = 1.0-(rssi-GOOD_RSSI)/(BAD_RSSI-GOOD_RSSI)   # Map to 0..1
                radioGoodness = 1.0 - math.pow((1.0-radioGoodness), 4)      # Skew heavily towards "good"
                prob *= radioGoodness
            self.commsOK = prob > random.random()

        deltaTime = random.expovariate(1.0 / self.commsUpDownPeriod)
        deltaTime = min(deltaTime, self.commsUpDownPeriod * 100.0) # Limit long tail
        sim.injectEventDelta(deltaTime, self.tickCommsUpDown, self)

    def doComms(self, properties):
        if self.commsOK:
            updateCallback(properties)
            logEntry(properties)

    def getProperty(self, propName):
        return self.properties[propName]

    def propertyExists(self, propName):
        return propName in self.properties
    
    def propertyAbsent(self, propName):
        return not self.propertyExists(propName)
    
    def setProperty(self, propName, value):
        newProps = { propName : value, "$ts" : sim.getTime1000(), "$id" : self.properties["$id"] }
        self.properties.update(newProps)
        self.doComms(newProps)

    def setProperties(self, newProps):
        newProps.update({ "$ts" : sim.getTime1000(), "$id" : self.properties["$id"] })  # Force ID and timestamp to be correct
        self.properties.update(newProps)
        self.doComms(newProps)

    def tickBatteryDecay(self, _):
        v = self.getProperty("battery")
        if v > 0:
            self.setProperty("battery", v-1)
            sim.injectEventDelta(self.batteryLife / 100.0, self.tickBatteryDecay, self)
        else:
            if self.batteryAutoreplace:
                logging.info("Auto-replacing battery")
                self.setProperty("battery",100)
                sim.injectEventDelta(self.batteryLife / 100.0, self.tickBatteryDecay, self)

    def tickHourly(self, _):
        if self.propertyAbsent("battery") or (self.getProperty("battery") > 0):
            self.setProperty("light", solar.sunBright(sim.getTime(),
                                                    (float(device.getProperty(self,"longitude")),float(device.getProperty(self,"latitude")))
                                                    ))
            sim.injectEventDelta(sim.hours(1), self.tickHourly, self)


# Model for comms unreliability
# -----------------------------
# Two variables define comms (un)reliability:
# a) updownPeriod: (secs) The typical period over which comms might change between working and failed state. We use an exponential distribution with this value as the mean.
# b) reliability: (0..1) The chance of comms working at any moment in time
# The comms state is then driven independently of other actions.
# 
# Chance of comms failing at any moment is [0..1]
# Python function random.expovariate(lambd) returns values from 0 to infinity, with most common values in a hump in the middle
# such that that mean value is 1.0/<lambd>
