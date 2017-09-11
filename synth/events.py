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

# TODO: Make actions pluggable?

import device_factory
from datetime import datetime
import isodate
import logging

class Events():
    def __init__(self, instance_name, restart_log, client, engine, updateCallback, eventList):
        """<params> is a list of events"""
        self.client = client
        self.engine = engine
        self.updateCallback = updateCallback
        self.instance_name = instance_name

        mode = "at"
        if restart_log:
            mode = "wt"
        self.logfile = open("../synth_logs/"+instance_name+".evt", mode, 0)    # Unbuffered
        self.logfile.write("*** New simulation starting at real time "+datetime.now().ctime()+" (local)\n")

        t = engine.get_now()
        for event in eventList:
            timedelta = event["at"]    # MUST specify a time and an action
            action = event["action"]
            repeats = event.get("repeats", 1)    # MAY also specify a repeat and interval
            interval = event.get("interval","PT0S")

            while repeats > 0:
                # Built-in actions
                if "create_device" in action:
                    device_factory.create_device(   t, instance_name, client, engine,
                                                    updateCallback,self.logfile,
                                                    action["create_device"])
                else:   # Plug-in actions
                    for k in action.keys():
                        if k in dir(client):
                            logging.info("Calling plug-in client action "+str(k))
                            getattr(client, k)(action[k])    # Programmatically call the method
                        else:
                            logging.error("Ignoring event action "+str(k)+" (not a built-in action, nor an action of a loaded client)")
##                    
##                elif "delete_demo_devices" in action:
##                    if "deleteDemoDevices" in dir(client):
##                        client.deleteDemoDevices()
##                else:
##                    logging.warning("Ignoring unknown event action type "+str(event["action"]))

                t += isodate.parse_duration(interval).total_seconds()
                repeats -= 1

    def flush(self):
        """Call at exit to clean up."""
        self.logfile.flush()
