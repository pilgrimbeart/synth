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
import isodate
import logging

class Events():
    def __init__(self, client, engine, updateCallback, logfile, eventList):
        """<params> is a list of events"""
        self.client = client
        self.engine = engine
        self.updateCallback = updateCallback
        self.logfile = logfile

        t = engine.get_now()
        for event in eventList:
            timedelta = event["at"]    # MUST specify a time and an action
            action = event["action"]
            repeats = event.get("repeats", 1)    # MAY also specify a repeat and interval
            interval = event.get("interval","PT0S")

            while repeats > 0:
                if "create_device" in action:
                    device_factory.create_device(t, client, engine, updateCallback, logfile,
                                action["create_device"])
                elif "delete_demo_devices" in action:
                    if "deleteDemoDevices" in dir(client):
                        client.deleteDemoDevices()
                else:
                    logging.warning("Ignoring unknown event action type "+str(event["action"]))

                t += isodate.parse_duration(interval).total_seconds()
                repeats -= 1
