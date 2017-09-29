#!/usr/bin/env python
"""
Events
======
The *events* section of a scenario file is a list of events to trigger during the simulation run. Each event requires at least::

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

Optionally, an event can repeat, so for example the scneario below starts with the creation of 10 devices, one per minute::

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

Run a query on historical data::

    "query" : {
        "expression" : "$ts < ago(30)"
    }

Bulk upload all events generated so far to the client::

    "bulk_upload" : {
    }

Resend to the client the newest-known value of every property of every devices (aka the 'top')::

    "send_top" : {
    }

Execute any action defined by the current Synth client (e.g. AWS, DevicePilot, filesystem etc.)::

    "client.<action>" {
        <whatever parameters it expects>
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

from datetime import datetime
import logging
import json
import pendulum, isodate
import device_factory
from common import query
from common import evt2csv
from common import ISO8601
from common import json_writer

LOG_DIRECTORY = "../synth_logs/"

class Events():
    def __init__(self, instance_name, restart_log, client, engine, eventList):
        """<params> is a list of events"""
        def callback(device_id, time, properties):
            write_event_log(properties)
            client.update_device(device_id, time, properties)

        def query_action(params):
            events = evt2csv.read_evt_str("".join(self.logtext))
            query.do_query(params, events)
            
        def client_action(args):
            (name, params) = args
            if "PLUGIN_"+name in dir(client):
                logging.info("Plug-in client action "+str(name))
                getattr(client, "PLUGIN_"+name)(params)    # Programmatically call the method
            else:
                logging.error("Ignoring action '"+str(name)+"' as client "+str(client.__class__.__name__)+" does not support it")

        def write_event_log(properties):
            """Write .evt and .json entries, and update top"""
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

            self.json_stream.write_event(properties)

            self.update_top(properties)

            self.event_count += 1
            
        self.client = client
        self.event_count = 0

        self.file_mode = "at"
        if restart_log:
            self.file_mode = "wt"
        self.logfile = open(LOG_DIRECTORY+instance_name+".evt", self.file_mode, 0)    # Unbuffered
        self.logfile.write("*** New simulation starting at real time "+datetime.now().ctime()+" (local)\n")

        self.json_stream = json_writer.Stream(instance_name)

        self.logtext = []   # TODO: Probably a Bad Idea to store this in memory. Instead when we want this we should probably close the logfile, read it and then re-open it. We store as an array because appending to a large string gets very slow

        self.top_devices = {}

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
                # Built-in actions (yes, these should really be plug-in too!)
                if action is None:
                    pass
                elif "create_device" in action:
                    engine.register_event_at(at_time,
                                             device_factory.create_device,
                                             (instance_name, client, engine, callback, action["create_device"]))
                elif "query" in action:
                    engine.register_event_at(at_time,
                                             query_action,
                                             action["query"])
                elif "bulk_upload" in action:
                    engine.register_event_at(at_time,
                                             self.bulk_upload,
                                             0)
                elif "send_top" in action:
                    engine.register_event_at(at_time,
                                             self.send_top,
                                             0)
                else:   # Plug-in actions
                    name = action.keys()[0]
                    if not name.startswith("client."):
                        logging.error("Ignoring unrecognised action "+name)
                    engine.register_event_at(at_time,
                                             client_action,
                                             (name[7:], action[name]))
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
        self.json_stream.close()

    def update_top(self, new_properties):
        """ 'top' means the latest-known value of each property, for each device.
            The structure of top is:
                A set of devices
                    Each of which is a set of properties
                        Each of which is a (time, value) tuple """
        new_id = new_properties["$id"]
        new_ts = new_properties["$ts"]
        if not new_id in self.top_devices:
            self.top_devices[new_id] = {}
        existing_props = self.top_devices[new_id]
        for new_prop, new_value in new_properties.iteritems():
            if new_prop not in existing_props:
                existing_props[new_prop] = (new_ts, new_value)
            else:
                existing_ts = existing_props[new_prop][0]
                if new_ts >= existing_ts:   # Only update if timestamp is newer
                    existing_props[new_prop] = (new_ts, new_value)

##        print "update_top():"
##        print "new_properties:"
##        print json.dumps(new_properties, indent=4, sort_keys=True)
##        print "so top now:"
##        print json.dumps(self.top_devices, indent=4, sort_keys=True)        

    def send_top(self, _):
        """Send top (latest) value of all properties on all devices to the client"""
        logging.info("Send_top")
        for dev, proptuples in self.top_devices.iteritems():
            props = {}
            for name,time_and_value in proptuples.iteritems():  # Assemble normal properties set (without times)
                props[name] = time_and_value[1]
            logging.info("Resending latest property values (of which there are "+str(len(props))+") for device "+str(dev))
            print props
            self.client.update_device(props["$id"], props["$ts"], props)

    def bulk_upload(self, _):
        self.json_stream.close()    # Close off final file 
        self.client.bulk_upload(self.json_stream.files_written)
