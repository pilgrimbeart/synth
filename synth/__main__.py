#!/usr/bin/env python
#
# Top-level module for the SYNTH project
# Generate and exercise synthetic devices for testing and demoing DevicePilot
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

from common import importer
import logging, math, time, sys, json, threading, subprocess, re, traceback
import random   # Might want to replace this with something we control
from datetime import datetime
from geo import geo
import peopleNames
import ISO8601
import device
import zeromq_rx


getSimTime = None   # TODO: Find a more elegant way for logging to discover simulation time

# Set up Python logger to report simulated time
def inSimulatedTime(self,secs=None):
    if getSimTime:
        t = getSimTime()
    else:
        t = 0
    return ISO8601.epochSecondsToDatetime(t).timetuple()  # Logging might be emitted within sections where simLock is acquired, so we accept a small chance of duff time values in log messages, in order to allow diagnostics without deadlock

def initLogging():
    logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S'
                    )
    logging.Formatter.converter=inSimulatedTime # Make logger use simulated time

initLogging()




def merge(a, b, path=None): # From https://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107
    """Deep merge dict <b> into dict <a>, overwriting a with b for any overlaps"""
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


    
def randList(start, delta, n):
    """Create a sorted list of <n> whole numbers ranging between <start> and <delta>."""
    L = [start + random.random()*delta for x in range(n)]
    return sorted(L)

def readParamfile(filename):
    try:
        s = open("scenarios/"+filename,"rt").read()
    except:
        s = open("../synth_accounts/"+filename,"rt").read()
    return s

def main():
    global getSimTime
    
    def createDevice(engine):
        deviceNum = device.numDevices()
        (lon,lat) = pp.pickPoint()
        (firstName, lastName) = (peopleNames.firstName(deviceNum), peopleNames.lastName(deviceNum))
        firmware = random.choice(["0.51","0.52","0.6","0.6","0.6","0.7","0.7","0.7","0.7"])
        operator = random.choice(["O2","O2","O2","EE","EE","EE","EE","EE"])
        if operator=="O2":
            radioGoodness = 1.0-math.pow(random.random(), 2)    # Skewed towards 1
        else:
            radioGoodness = math.pow(random.random(), 2)        # Skewed towards 0
        props = {   "$id" : "-".join([format(random.randrange(0,255),'02x') for i in range(6)]), # A 6-byte MAC address 01-23-45-67-89-ab
                    "$ts" : engine.get_now_1000(),
                    "is_demo_device" : True,    # A flag which lets us selectively delete later
                    "label" : "Thing "+str(deviceNum),
                    "longitude" : lon,
                    "latitude" : lat,
                    "first_name" : firstName,
                    "last_name" : lastName,
                    "full_name" : firstName + " " + lastName,
                    "factoryFirmware" : firmware,
                    "firmware" : firmware,
                    "operator" : operator,
                    "rssi" : ((1-radioGoodness)*(device.BAD_RSSI-device.GOOD_RSSI)+device.GOOD_RSSI),
                    "battery" : 100
                }
        client.add_device(props["$id"], engine.get_now(), props)
        d = device.device(props["$id"], engine.get_now(), props, engine)
        if "comms_reliability" in params:
#            d.setCommsReliability(upDownPeriod=0.5*60*60*24, reliability=1.0-math.pow(random.random(), 2)) # pow(r,2) skews distribution towards reliable end
            d.setCommsReliability(upDownPeriod=0.5*60*60*24, reliability=params["comms_reliability"])
        d.setBatteryLife(params["battery_life_mu"], params["battery_life_sigma"], "battery_autoreplace" in params)

    def postWebEvent(webParams):    # CAUTION: Called asynchronously from the web server thread
        if "action" in webParams:
            if webParams["action"] == "event":
                if webParams["headers"]["Instancename"]==params["instance_name"]:
                    mini = float(params["web_response_min"])
                    maxi = float(params["web_response_max"])
                    engine.theInstance.register_event_in(mini + random.random()*maxi, device.externalEvent, webParams)

    params = {}

    # Default params. Override these by specifying one or more JSON files on the command line.
    params = merge(params, {
        "instance_name" : "default",    # Used for naming log files
        "initial_action" : None,
        "device_count" : 10,
        "install_timespan" : 1*60,
        "battery_life_mu" : 50*60,
        "battery_life_sigma" : 1*60,
        "comms_reliability" : 1.0,  # Either a fractional number, or a specification string
        "web_key" : 12345,
        "web_response_min" : 3,  # (s) Range of delay to respond to an incoming web request
        "web_response_max" : 10
        })


    logging.info("*** Synth starting at real time "+str(datetime.now())+" ***")
    
    for arg in sys.argv[1:]:
        if arg.startswith("{"):
            logging.info("Setting parameters "+arg)
            params = merge(params, json.loads(arg))
        elif "=" in arg:    # RHS always interpreted as a string
            logging.info("Setting parameter "+arg)
            (key,value) = arg.split("=",1)  # split(,1) so that "a=b=c" means "a = b=c"
            params = merge(params, { key : value })
        else:
            logging.info("Loading parameter file "+arg)
            s = readParamfile(arg)
            s = re.sub("#.*$","",s,flags=re.MULTILINE) # Remove Python-style comments
            params = merge(params, json.loads(s))
    
    logging.info("Parameters:\n"+json.dumps(params, sort_keys=True, indent=4, separators=(',', ': ')))

    Tstart = time.time()
    random.seed(12345)  # Ensure reproduceability

    if not "client" in params:
        logging.error("No client defined to receive simulation results")
        return
    client = importer.get_class('client', params['client']['type'])(params['client'])

    if not "engine" in params:
        logging.error("No simulation engine defined")
        return
    engine = importer.get_class('engine', params['engine']['type'])(params['engine'], client.enter_interactive)
    getSimTime = engine.get_now_no_lock

    device.init(updatecallback=client.update_device, logfileName=params["instance_name"])

    zeromq_rx.init(postWebEvent)

    pp = geo.pointPicker()
    if "area_centre" in params:
        pp.setArea([params["area_centre"], params["area_radius"]])

    # Set up the world
    
##    if dp:
##        if params["initial_action"]=="deleteExisting":      # Recreate world from scratch
##            dp.deleteAllDevices()   # !!! TODO: Delete properties too.
##        if params["initial_action"]=="deleteDemo":  # Delete only demo devices (slow)
##            dp.deleteDevicesWhere('(is_demo_device == true)')
##        if params["initial_action"]=="loadExisting":       # Load existing world
##            for d in dp.getDevices():
##                device.device(d)
##    if aws:
##        if params["initial_action"] in ["deleteExisting", "deleteDemo"]:
##            aws.deleteDemoDevices()
##        # Loading device state from AWS not yet supported
##
##    if "device_setup" in params:
##        if params["device_setup"]=="whitelees":
##            whitelees.deviceSetup()
##        else:
##            print "Unrecognised device_setup:",params["device_setup"]
##            exit(-1)
##    else:
##        if params["initial_action"] != "loadExisting":
    times = randList(engine.get_now(), params["install_timespan"], params["device_count"])
    engine.register_events_at(times, createDevice, engine)

    logging.info("Simulation starts")
    try:
        while engine.events_to_come():
            engine.next_event()
            client.tick()
    except:
        logging.error(traceback.format_exc()) # Report any exception, but continue to clean-up anyway

    device.flush()
    client.flush()
    logging.info("Simulation ends")

    logging.info("Elapsed real time: "+str(int(time.time()-Tstart))+" seconds")

if __name__ == "__main__":
    main()
