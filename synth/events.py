#!/usr/bin/env python
#
"""EVENTS
   Spawn events at given times"""
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

JSON_EVENTS_PER_FILE = 10000

class Events():
    def __init__(self, instance_name, restart_log, client, engine, updateCallback, eventList):
        """<params> is a list of events"""
        def query_action(params):
            events = evt2csv.read_evt_str("".join(self.logtext))
            query.do_query(params, events)
            
        def plugin_action(args):
            (name, params) = args
            if name in dir(client):
                logging.info("Calling plug-in client action "+str(name))
                getattr(client, name)(params)    # Programmatically call the method
            else:
                logging.error("Ignoring unknown event action '"+str(name)+"' (neither an inbuilt action, nor an action of a loaded client)")

        def write_log(properties):
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
            
            self.json_check_next_file()
            jprops = properties.copy()
            jprops["$ts"] = int(jprops["$ts"] * 1000) # Convert timestamp to ms as that's what DP uses internally in JSON files
            if self.json_events_in_this_file > 0:
                self.jsonfile.write(",\n")
            self.jsonfile.write(json.dumps(jprops, sort_keys=True))

            self.event_count += 1
            
        self.client = client
        self.engine = engine
        self.updateCallback = updateCallback
        self.instance_name = instance_name
        self.event_count = 0

        self.file_mode = "at"
        if restart_log:
            self.file_mode = "wt"
        self.logfile = open("../synth_logs/"+instance_name+".evt", self.file_mode, 0)    # Unbuffered
        self.logfile.write("*** New simulation starting at real time "+datetime.now().ctime()+" (local)\n")
        self.jsonfile = None
        self.logtext = []   # TODO: Probably a Bad Idea to store this in memory. Instead when we want this we should probably close the logfile, read it and then re-open it. We store as an array because appending to a large string gets very slow

        at_time = engine.get_now()
        for event in eventList:
            timespec = event["at"]
            if timespec[0] in "-+P":    # Time relative to current sim time
                at_time = at_time + isodate.parse_duration(timespec).total_seconds()
            else:
                at_time = ISO8601.to_epoch_seconds(timespec)

            action = event["action"]
            repeats = event.get("repeats", 1)    # MAY also specify a repeat and interval
            interval = event.get("interval","PT0S")

            while repeats > 0:
                # Built-in actions (yes, these should really be plug-in too!)
                if "create_device" in action:
                    engine.register_event_at(at_time,
                                             device_factory.create_device,
                                             (instance_name, client, engine, updateCallback, write_log, action["create_device"]))
                elif "query" in action:
                    engine.register_event_at(at_time,
                                             query_action,
                                             action["query"])
                else:   # Plug-in actions
                    name = action.keys()[0]
                    engine.register_event_at(at_time,
                                             plugin_action,
                                             (name, action[name]))
##                    
##                elif "delete_demo_devices" in action:
##                    if "deleteDemoDevices" in dir(client):
##                        client.deleteDemoDevices()
##                else:
##                    logging.warning("Ignoring unknown event action type "+str(event["action"]))

                at_time += isodate.parse_duration(interval).total_seconds()
                repeats -= 1

    def json_move_to_next_file(self):
        """Move to next json file"""
        if self.jsonfile is None:
            self.json_file_count = 1
        else:
            self.json_close_file()
            self.json_file_count += 1

        filename = "../synth_logs/" + self.instance_name + "%05d" % self.json_file_count + ".json"
        logging.info("Starting new logfile "+filename)
        self.jsonfile = open(filename, self.file_mode, 0)
        self.jsonfile.write("[\n")
        self.json_events_in_this_file = 0

    def json_check_next_file(self):
        """Check if time to move to next json file"""
        if self.jsonfile is None:
            self.json_move_to_next_file()
            return
        if self.json_events_in_this_file >= JSON_EVENTS_PER_FILE-1:
            self.json_move_to_next_file()
            return
        self.json_events_in_this_file += 1

    def json_close_file(self):
        if self.jsonfile is not None:
            # self.jsonfile.seek(-3,1)    # Move back over final comma, linefeed, newline
            self.jsonfile.write("\n]\n")
            self.jsonfile.close()
            self.jsonfile = None

    def flush(self):
        """Call at exit to clean up."""
        self.logfile.flush()
        self.json_close_file()
