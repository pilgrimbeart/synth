#!/usr/bin/env python
#
# DEVICE_FACTORY
# A device factory
#
# TODO: Turn this into a class
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
from common import importer
import datetime
import logging, traceback
import pendulum, isodate
from devices.basic import Basic

devices = []

def randList(start, delta, n):
    """Create a sorted list of <n> whole numbers ranging between <start> and <delta>."""
    L = [start + random.random()*delta for x in range(n)]
    return sorted(L)

def composeClass(classNames):
    """Create a composite class from a list of class names."""
    classes = []
    for className in classNames:
        classes.append(importer.get_class('device', className))
    classes.append(Basic)   # Class at END of the list is the root of inheritance
    return type("compositeDeviceClass",tuple(classes),{})

def createDevice((instance_name, client, engine, updateCallback, logfile, params)):
    def callback(device_id, time, properties):
        logEntry(logfile, time, properties)
        updateCallback(device_id, time, properties)

    global devices
    deviceNum = numDevices()

    if "functions" in params:
        C = composeClass(params["functions"].keys())        # Create a composite device class from all the given class names
        d = C(instance_name, engine.get_now(), engine, callback, params["functions"])   # Instantiate it
    else:
        d = Basic(instance_name, engine.get_now(), engine, callback, params)
    client.add_device(d.properties["$id"], engine.get_now(), d.properties)

    if getDeviceByProperty("$id",d.properties["$id"]) != None:
        logging.error("FATAL: Attempt to create duplicate device "+str(d.properties["$id"]))
        exit(-1)
    devices.append(d)

def create_device(time, instance_name, client, engine, updateCallback, logfile, params):
    engine.register_event_at(time, createDevice, (instance_name,client,engine,updateCallback,logfile,params))

def numDevices():
    global devices
    n = len(devices)
    return n

def getDeviceByProperty(prop, value):
    global devices
    for d in devices:
        if prop in d.properties:
            if d.properties[prop]==value:
                return d
    return None

def logEntry(logfile, time, properties):
    logfile.write(pendulum.from_timestamp(time).to_datetime_string()+" ")
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

##def logString(s, time=None):
##    logging.info(s)
##    if time:
##        ts = pendulum.from_timestamp(time).to_datetime_string() + " "
##    else:
##        ts = ""
##    logfile.write(ts+s+"\n")

def externalEvent(params):
    """Accept events from outside world.
    (these have already been synchronised via the event queue so we don't need to worry about thread-safety here)"""
    global devices
    body = params["body"]
    try:
        logging.info("external Event received: "+str(params))
        for d in devices:
            if d.properties["$id"] == body["deviceId"]:
                arg = body.get("arg", None)
                d.external_event(body["eventName"], arg)
                return
        logging.error("No such device "+str(body["deviceId"])+" for incoming event "+str(body["eventName"]))
    except Exception as e:
        logging.error("Error processing externalEvent: "+str(e))
        logging.error(traceback.format_exc())
        
