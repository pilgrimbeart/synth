"""DEVICE_FACTORY
   A device factory. TODO: Turn this into a class."""
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

import logging
import traceback
import json
import pendulum
from common import importer
from common import conftime
from devices.basic import Basic

devices = []

def compose_class(class_names):
    """Create a composite class from a list of class names."""
    classes = []
    for class_name in class_names:
        if class_name != "basic":   # Normally this is not explicitly specified, so is implicit, but even it is explict we want to ensure that it's the last class added
            classes.append(importer.get_class('device', class_name))
    classes.append(Basic)   # Class at END of the list is the root of inheritance
    return type("compositeDeviceClass", tuple(classes), {})

def create_device(args):
    global devices
    (instance_name, client, engine, update_callback, context, params) = args
    
    device_num = num_devices()

    if "functions" in params:
        C = compose_class(params["functions"].keys())        # Create a composite device class from all the given class names
        d = C(instance_name, engine.get_now(), engine, update_callback, context, params["functions"])   # Instantiate it
    else:
        d = Basic(instance_name, engine.get_now(), engine, update_callback, context, params)
    client.add_device(d.properties["$id"], engine.get_now(), d.properties)

    if "stop_at" in params:
        at_time = conftime.richTime(params["stop_at"])
        engine.register_event_at(at_time, stop_device, (engine,d), None)

    if get_device_by_property("$id", d.properties["$id"]) != None:
        logging.error("FATAL: Attempt to create duplicate device "+str(d.properties["$id"]))
        exit(-1)
    devices.append(d)

    return d

def stop_device(args):
    # We stop a device by removing all its pending events
    (engine,device) = args
    logging.info("stopping device "+str(device)+" "+str(device.properties["$id"]))
    engine.remove_all_events_for_device(device)
    # devices.remove(d) # we no longer delete it
    
def num_devices():
    global devices
    n = len(devices)
    return n

def get_device_by_property(prop, value):
    global devices
    for d in devices:
        if prop in d.properties:
            if d.properties[prop] == value:
                return d
    return None

def get_devices_by_property(prop, value):
    # Same as above, but return list of all matching devices
    global devices
    devs = []
    for d in devices:
        if prop in d.properties:
            if d.properties[prop] == value:
                devs.append(d)
    return devs

##def logString(s, time=None):
##    logging.info(s)
##    if time:
##        ts = pendulum.from_timestamp(time).to_datetime_string() + " "
##    else:
##        ts = ""
##    logfile.write(ts+s+"\n")

def external_event(params):
    """Accept events from outside world.
    (these have already been synchronised via the event queue so we don't need to worry about thread-safety here)"""
    global devices
    body = params["body"]
    try:
        logging.debug("external Event received: "+str(params))
        for d in devices:
            if d.properties["$id"] == body["deviceId"]:
                arg = body.get("arg", None)
                d.external_event(body["eventName"], arg)
                return
        logging.error("No such device "+str(body["deviceId"])+" for incoming event "+str(body["eventName"]))
    except Exception as e:
        logging.error("Error processing external_event: "+str(e))
        logging.error(traceback.format_exc())


def close():
    """Close all devices"""
    for d in devices:
        d.close()
