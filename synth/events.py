#!/usr/bin/env python
"""
Events
======
The *events* section of a scenario file is a list of events to trigger during the simulation run. An event is typically specified by::

        "at" : "2017-01-01T00:00:00"	# The time at which the event happens (can be relative)
        "action" : {}	# The action to conduct. Generally this create_device, but can also be a client-specific method

The "at" time can be absolute ("2017-01-01T00:00:00"), relative to the previous event ("PT3M") or "end" to schedule events at the end of the simulation.
A common pattern is to create a sequence of actions all happening at relative times using `at="PTxx"`.
If the relative time is "PT0S" then the event will be scheduled for the same (*) time as the previous event.
Relative times can even be negative to add an event *before* the previous event!

For convenience:

    * If you omit the "at" then it defaults to "PT0S" i.e. "immediately after the previous event"
    * If you omit the "action" then it simply acts to set the time for any subsequent relative events

(*) The `sim` engine guarantees that events which are scheduled for the same time will be executed in the order that they are defined.

Optionally, an event can repeat, with optionally an interval between each repeat, so for example the scenario below starts with the creation of 10 devices, one per minute::

    "events" : [
        {
        "at" : "PT0S",
        "repeats" : 10,
        "interval" : "PT1M",
        "action": {
            "create_device" : {
                "functions" : {
                    ...
                }
            }
        }
    ]

Actions
=======
Create a device::

    "create_device" : {
        "functions" : {
                ...
        }
    }

Change arbitrary device properties with arbitrary timestamps::

    "change_property" : {
        "identity_property" : "name_of_property",   # e.g. "$id" - which property is used to identify device
        "identity_value" : value_of_property,       # e.g. "01-02-03-04-05-06"
        "property_name" : "name_of_property",
        "property_value" : value_of_property  [can be string, number or boolean]
        "$ts" : "time_specification"    # e.g. "-P1D" or "2000-01-01T00:00:00" - optional, if omitted change is stamped with current simulation time
        "is_attribute" : False  # If true, then instead of this setting a named property of the device, it sets an attribute of the object managing the device (i.e. a way to change the device behaviour)
    }
    
Execute an action on whichever Synth client is in use (e.g. aws, devicepilot, filesystem etc. - see docs for each client)::

    "client.<action>" {
        <whatever parameters it expects>
    }

Get Synth to run a query on the historical data it has just generated [TODO: code not yet complete!]::

    "query" : {
        "expression" : "$ts < ago(30)"
    }

Install an anomaly-analyser::

    "install_analyser" {
    }
"""
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

import os, errno
from datetime import datetime
import logging
import json
import pendulum, isodate
import device_factory
import model
from common import query
from common import evt2csv
from common import ISO8601
from common import conftime
from analysis import analyse

LOG_DIRECTORY = "../synth_logs/"

def mkdir_p(path):
    try:
        os.makedirs(path)
        logging.info("Created log directory "+path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class Events():
    def __init__(self, client, engine, instance_name, context, eventList):
        """<params> is a list of events. Note that our .event_count property is read from outside."""
        def update_callback(device_id, time, properties):
            for c in self.update_callbacks:
                properties.update(c(properties))  # We MERGE the results of the callback with the original message
            write_event_log(properties)
            client.update_device(device_id, time, properties)

        def query_action(params):
            events = evt2csv.read_evt_str("".join(self.logtext))
            query.do_query(params, events)
            
        def change_property_action(params):
            def set_it(d):
                if params.get("is_attribute", False):
                    d.__dict__[params["property_name"]] = params["property_value"]
                    logging.info("Set attribute "+str(params["property_name"])+" on device "+d.get_property("$id")+" to "+str(params["property_value"]))
                else:
                    d.set_property(params["property_name"], params["property_value"], timestamp=ts)
                    logging.info("Set property "+str(params["property_name"])+" on device "+d.get_property("$id")+" to "+str(params["property_value"]))

            d = device_factory.get_devices_by_property( params["identity_property"],
                                                       params["identity_value"])
            logging.info("change property acting on "+str(len(d))+" matching devices")

            if "$ts" in params:
                ts = conftime.richTime(params["$ts"])
            else:
                ts = None

            logging.info("change_property "+str(params))
            for the_d in d:
                set_it(the_d)

        def client_action(args):
            (name, params) = args
            if "PLUGIN_"+name in dir(client):
                logging.info("Plug-in client action "+str(name))
                getattr(client, "PLUGIN_"+name)(params)    # Programmatically call the method
            else:
                logging.error("Ignoring action '"+str(name)+"' as client "+str(client.__class__.__name__)+" does not support it")

        def write_event_log(properties):
            """Write .evt entry"""
            s = pendulum.from_timestamp(properties["$ts"]).to_datetime_string()+" "

            for k in sorted(properties.keys()):
                s += str(k) + ","
                try:
                    s += json.dumps(properties[k])  # Use dumps not str so we preserve type in output
                    # s += properties[k].encode('ascii', 'ignore') # Python 2.x barfs if you try to write unicode into an ascii file
                except:
                    s += "<unicode encoding error>"
                s += ","
            s += "\n"
            self.logfile.write(s)
            self.logtext.append(s)

            self.event_count += 1

        restart_log = context.get("restart_log",True)
        
        self.client = client
        self.event_count = 0
        self.update_callbacks = []

        mkdir_p(LOG_DIRECTORY)
        self.file_mode = "at"
        if restart_log:
            self.file_mode = "wt"
        self.logfile = open(LOG_DIRECTORY+instance_name+".evt", self.file_mode)    # This was unbuffered, but Python3 now doesn't allow text files to be unbuffered
        self.logfile.write("*** New simulation starting at real time "+datetime.now().ctime()+" (local)\n")

        self.logtext = []   # TODO: Probably a Bad Idea to store this in memory. Instead when we want this we should probably close the logfile, read it and then re-open it. We store as an array because appending to a large string gets very slow

        at_time = engine.get_now()
        for event in eventList:
            timespec = event.get("at", "PT0S")
            if timespec == "end":
                end_time = engine.get_end_time()    # This may not be a time
                assert type(end_time) in [int, float], "An event is defined at 'end', but simulation end time is not a definitive time"
                at_time = engine.get_end_time() - 0.001 # Ensure they happen BEFORE the end, as sim end time is non-inclusive
            elif timespec[0] in "-+P":    # Time relative to current sim time
                at_time = at_time + isodate.parse_duration(timespec).total_seconds()
            else:
                at_time = ISO8601.to_epoch_seconds(timespec)

            action = event.get("action", None)
            repeats = event.get("repeats", 1)    # MAY also specify a repeat and interval
            interval = event.get("interval","PT0S")

            while repeats > 0:
                # Built-in actions. TODO: Make these plug-in too?
                if action is None:
                    pass
                elif "create_device" in action:
                    engine.register_event_at(at_time,
                                             device_factory.create_device,
                                             (instance_name, client, engine, update_callback, context, action["create_device"]),
                                             None)
                elif "use_model" in action:
                    engine.register_event_at(at_time,
                            model.use_model,
                            (instance_name, client, engine, update_callback, context, action["use_model"]), None)
                elif "query" in action:
                    engine.register_event_at(at_time,
                                             query_action,
                                             action["query"],
                                             None)
                elif "change_property" in action:
                    engine.register_event_at(at_time,
                                             change_property_action,
                                             action["change_property"],
                                             None)
                elif "install_analyser" in action:
                    logging.info("Installing analyser")
                    self.analyser = analyse.Analyser()
                    self.update_callbacks.append(self.analyser.process)
                else:   # Plug-in actions
                    name = action.keys()[0]
                    if not name.startswith("client."):
                        logging.error("Ignoring unrecognised action "+name)
                    else:
                        engine.register_event_at(at_time,
                                                 client_action,
                                                 (name[7:], action[name]),
                                                 None)
##                    
##                elif "delete_demo_devices" in action:
##                    if "deleteDemoDevices" in dir(client):
##                        client.deleteDemoDevices()
##                else:
##                    logging.warning("Ignoring unknown event action type "+str(event["action"]))

                at_time += isodate.parse_duration(interval).total_seconds()
                repeats -= 1

    def flush(self):
        """Call at exit to clean up."""
        self.logfile.flush()
