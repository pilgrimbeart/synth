#!/usr/bin/env python
"""
Events
======
The *events* section of a scenario file is a list of events to trigger during the simulation run. An event is typically specified by::

        "at" : "2017-01-01T00:00:00"	# The time at which the event happens (can be relative)
        "action" : {}	# The action to conduct. Generally this create_device, but can also be a client-specific method

The "at" time can be:
1) An absolute time ("2017-01-01T00:00:00")
2) A time relative to the previous event ("PT3M" or even "-PT3D" to jump back in time)
3) At the end of the simulation ("end")
4) Relative to when the simulation is run ("now-P3D")

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
        "time_advance" : true,
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
#
# TODO: Started writing a "sharding" mechanism, to split a Synth run across multiple instances. But not finished as
#       for now it's good-enough to create large loads by just "exploding" device IDs 
#       (so an explode factor of 100 will generate 100 output devices for every 1 simulated device, and they'll be identical (apart from id))
# 
import os, errno
import sys
import time
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
import functools

LOG_DIRECTORY = "../synth_logs/"

METADATA_DIRECTORY = "/tmp/synth_metadata/"

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

            if self.explode_factor is None:
                client.update_device(device_id, time, properties)
            else:
                new_props = properties.copy()
                for i in range(self.explode_factor):
                    eid = str(device_id) + "_" + str(i)    # Each exploded device is identical, except for trailing "-N" ID (and label, if exists)
                    new_props["$id"] = eid
                    if "label" in new_props:
                        new_props["label"] = properties["label"] + "_" + str(i) 
                    if self.do_write_log:
                        write_event_log(new_props)
                    client.update_device(eid, time, new_props)

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

            d = device_factory.get_devices_by_property( params["identity_property"], params["identity_value"])
            if "identity_property2" in params:
                d2 = device_factory.get_devices_by_property( params["identity_property2"], params["identity_value2"])
                d = list(set(d) & set(d2))
            logging.info("change property acting on "+str(len(d))+" matching devices")

            if "$ts" in params:
                ts = conftime.richTime(params["$ts"])
            else:
                ts = None

            logging.info("change_property "+str(params))
            for the_d in d:
                set_it(the_d)

        def dump_periodic_metadata(params):
            interval = isodate.parse_duration(params["interval"]).total_seconds()
            metadata_list = set(params["metadata"])
            metadata = []
            for d in device_factory.get_devices():
                p = {}
                for k,v in d.get_properties().items():
                    if k in metadata_list:
                        p[k] = v
                if len(p) > 0: 
                    # logging.info("For device " + d.get_property("$id") + " setting properties "+str(p))
                    # d.set_properties(p)
                    p["$id"] = d.get_property("$id")
                    metadata.append(p)
            fname_stem = METADATA_DIRECTORY + instance_name
            open(fname_stem + ".tmp","wt").write(json.dumps(metadata))
            os.rename(fname_stem + ".tmp", fname_stem + ".json")    # So change is atomic (don't want ^C to leave partially-written file)
            engine.register_event_at(engine.get_now() + interval, dump_periodic_metadata, params, None)

        def client_action(args):
            (name, params) = args
            if "PLUGIN_"+name in dir(client):
                logging.info("Plug-in client action "+str(name))
                getattr(client, "PLUGIN_"+name)(params)    # Programmatically call the method
            else:
                logging.error("Ignoring action '"+str(name)+"' as client "+str(client.__class__.__name__)+" does not support it")

        @functools.lru_cache(maxsize=128)
        def dt_string(t):
            return pendulum.from_timestamp(t).to_datetime_string() + " "    # For some reason, this is very slow

        def write_event_log(properties):
            """Write .evt entry"""
            s = dt_string(properties["$ts"])

            for k in sorted(properties.keys()):
                s += str(k) + ","
                try:
                    s += json.dumps(properties[k])  # Use dumps not str so we preserve type in output
                    # s += properties[k].encode('ascii', 'ignore') # Python 2.x barfs if you try to write unicode into an ascii file
                except:
                    logging.error("Encoding error in events.py::write_event_log")
                    s += "<unicode encoding error>"
                s += ","
            s += "\n"
            self.logfile.write(s)

            self.event_count += 1

        restart_log = context.get("restart_log", True)
        self.do_write_log = context.get("write_log", True)
        shard_size = context.get("shard_size", None)
        shard_start = context.get("shard_start", 0) # If not specified, we are shard 0, so get to create the other shards
        self.explode_factor = context.get("explode_factor", None)
        if self.explode_factor is not None:
            logging.info("Running with explode_factor="+str(self.explode_factor))

        self.event_count = 0
        self.update_callbacks = []
        device_count = 0   # Used to shard device creation

        if self.do_write_log:
            mkdir_p(LOG_DIRECTORY)
            self.file_mode = "at"
            if restart_log:
                self.file_mode = "wt"
            self.logfile = open(LOG_DIRECTORY+instance_name+".evt", self.file_mode)    # This was unbuffered, but Python3 now doesn't allow text files to be unbuffered
            self.logfile.write("*** New simulation starting at real time "+datetime.now().ctime()+" (local)\n")
        else:
            self.logfile = None
            logging.info("Not writing an event log")

        self.logtext = []   # TODO: Probably a Bad Idea to store this in memory. Instead when we want this we should probably close the logfile, read it and then re-open it. We store as an array because appending to a large string gets very slow

        at_time = engine.get_now()
        for event in eventList:
            timespec = event.get("at", "PT0S")
            if timespec.startswith("now"):
                dt = datetime.fromtimestamp(time.time()) # Take time in whole seconds (so if we ever want to repeat the run, we can start it at the exact same time)
                dt.microsecond = 0
                realtime = dt.timestamp()
                delta = isodate.parse_duration(timespec[3:]).total_seconds()
                at_time = realtime + delta
            elif timespec == "end":
                end_time = engine.get_end_time()    # This may not be a time
                assert type(end_time) in [int, float], "An event is defined at 'end', but simulation end time is not a definitive time"
                at_time = engine.get_end_time() - 0.001 # Ensure they happen BEFORE the end, as sim end time is non-inclusive
            elif timespec[0] in "-+P":    # Time relative to current 'at' time
                at_time = at_time + isodate.parse_duration(timespec).total_seconds()
            else:
                at_time = ISO8601.to_epoch_seconds(timespec)

            action = event.get("action", None)
            repeats = event.get("repeats", 1)    # MAY also specify a repeat and interval
            interval = event.get("interval","PT0S")
            time_advance = event.get("time_advance", True)

            insert_time = at_time
            while repeats > 0:
                # Built-in actions. TODO: Make these plug-in too?
                if action is None:
                    pass
                elif "create_device" in action:
                    do_create = True                 # Is this device in our shard?
                    if shard_size is not None:
                        if device_count < shard_start:
                            do_create = False
                        if device_count >= shard_start + shard_size:
                            do_create = False

                        if shard_start == 0:    # We're the first shard
                            if device_count > 0:
                                if (device_count % shard_size) == 0:
                                    logging.info("CREATE NEW SHARD for devices starting at "+str(device_count))
                                    args = sys.argv.copy()
                                    args = ["python3"] + args + ["{ shard_start : " + str(device_count) + " } "]
                                    logging.info(str(args))

                    if do_create:
                        engine.register_event_at(insert_time, device_factory.create_device,
                                             (instance_name, client, engine, update_callback, context, action["create_device"]),
                                             None)

                    device_count += 1
                elif "use_model" in action:
                    engine.register_event_at(insert_time,
                            model.use_model,
                            (instance_name, client, engine, update_callback, context, action["use_model"]), None)
                elif "query" in action:
                    engine.register_event_at(insert_time,
                                             query_action,
                                             action["query"],
                                             None)
                elif "change_property" in action:
                    engine.register_event_at(insert_time,
                                             change_property_action,
                                             action["change_property"],
                                             None)
                elif "install_analyser" in action:
                    logging.info("Installing analyser")
                    self.analyser = analyse.Analyser()
                    self.update_callbacks.append(self.analyser.process)
                elif "periodic_metadata" in action:
                    engine.register_event_at(insert_time, dump_periodic_metadata, action["periodic_metadata"], None)
                else:   # Plug-in actions
                    name = action.keys()[0]
                    if not name.startswith("client."):
                        logging.error("Ignoring unrecognised action "+name)
                    else:
                        engine.register_event_at(insert_time,
                                                 client_action,
                                                 (name[7:], action[name]),
                                                 None)
##                    
##                elif "delete_demo_devices" in action:
##                    if "deleteDemoDevices" in dir(client):
##                        client.deleteDemoDevices()
##                else:
##                    logging.warning("Ignoring unknown event action type "+str(event["action"]))

                insert_time += isodate.parse_duration(interval).total_seconds()
                repeats -= 1
            if time_advance:
                at_time = insert_time

    def flush(self):
        """Call at exit to clean up."""
        if self.logfile is not None:
            self.logfile.flush()
