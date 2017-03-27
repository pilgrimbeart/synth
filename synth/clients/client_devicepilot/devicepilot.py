#!/usr/bin/env python
#
# Drive the DevicePilot API
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

import httplib
import json
import logging
import requests
import time
import urllib

lastPostTime = 0

logging.getLogger("requests").setLevel(logging.WARNING)  # Suppress annoying connection messages from Requests


def set_headers(token):
    headers = {"Authorization": "Token {0}".format(token), "Content-Type": "application/json"}
    return headers


class Api:
    def __init__(self, url=None, key=None):
        logging.info("Initialising DevicePilot client")
        self.url = url
        self.key = key

        self.postQueue = []
        self.queueFlushCriterion = "messages"  # or "time" or "interactive"
        self.queueFlushLimit = 1000
        self.postCount = 0

    def set_queue_flush(self, criterion="messages", limit=1000):
        # queue_criterion/limit sets how often we flush messages to DevicePilot API
        # If criterion=="messages" then limit is number of messages, e.g. 1000
        # If criterion=="time" then limit is amount of simulated time passing, e.g. sim.days(30)
        # If criterion=="interactive" then limit is amount of real time passing, e.g. 1 (second)

        self.queueFlushCriterion = criterion
        self.queueFlushLimit = limit

    def post_device(self, device, historical=False):
        # DevicePilot API accepts either a single JSON object, or an array of such
        # If <historical> is true, DevicePilot doesn't calculate any dependent events (so e.g. won't send alerts)
        global lastPostTime
        lastPostTime = time.time()

        body = json.dumps(device)

        if isinstance(device, list):
            self.postCount += len(device)
        else:
            self.postCount += 1

        resp = None
        try:
            url = self.url + '/device-state'
            if historical:
                url = url + "?historical=true"
            resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)
        except httplib.HTTPException as err:
            logging.error("devicepilot.postDevice() couldn't create on server")
            logging.error(str(err))
            logging.error(str(device))

        if resp.status_code == 207:  # Multi-response
            for i in json.loads(resp.text):
                if (i["status"] < 200) or (i["status"] > 299):
                    logging.error("ERROR:" + str(i))
        else:
            if resp.status_code != requests.codes.ok and resp.status_code != requests.codes.created:
                logging.error("devicepilot.PostDevice() couldn't create on server")
                logging.error("Status code:" + str(resp.status_code))
                logging.error("Text:" + str(resp.text))
                logging.error("Body:" + str(body))

        return True

    def ready_to_flush(self):
        if self.queueFlushCriterion == "messages":
            if len(self.postQueue) >= self.queueFlushLimit:
                return True
        if self.queueFlushCriterion == "time":
            # Note that $ts properties in the post queue will be in epoch-MILLI seconds as that's what DP expects
            if self.postQueue[-1]["$ts"] - self.postQueue[0]["$ts"] >= self.queueFlushLimit * 1000:
                return True
        if self.queueFlushCriterion == "interactive":
            if time.time() - lastPostTime > self.queueFlushLimit:
                return True
        return False

    def post_device_q(self, device):

        if isinstance(device, list):
            for d in device:
                if d["$id"] == "device0":
                    pass  # logging.info(str(d))
                self.postQueue.extend(d.copy())
        else:
            if device["$id"] == "device0":
                pass  # logging.info(str(device))
            self.postQueue.append(device.copy())

        self.flush_post_queue_if_ready()

    def flush_post_queue_if_ready(self):
        if self.ready_to_flush():
            self.flush_post_queue()

    def flush_post_queue(self):
        if len(self.postQueue) > 0:
            logging.info("POSTing " + str(len(self.postQueue)) + " queued items into DevicePilot")
            self.post_device(self.postQueue, historical=True)
            self.postQueue = []

    def recalc_historical(self, an_id):
        logging.info("DevicePilot client finalising historical updates")
        self.post_device({"$id": an_id},
                         historical=False)
        # After a run of historical posts, posting anything with (historical==False)
        # triggers DevicePilot to update all its event calculations [we just need any valid id]
        assert requests.put(self.url + '/propertySummaries',
                            headers=set_headers(self.key)).status_code == 200
        # Tell DP that we should regen property summaries

    def enter_interactive(self, an_id):
        logging.info("DevicePilot client entering (interactive,1sec) mode")
        self.recalc_historical(an_id)
        self.queueFlushCriterion = "interactive"
        self.queueFlushLimit = 1

    def delete_all_devices(self):
        logging.info("Deleting all devices on this account...")
        assert requests.delete(self.url + "/devices", headers=set_headers(self.key)).status_code == 200
        logging.info("All devices deleted")

    def delete_devices_where(self, where_str):
        logging.info("Deleting all devices where " + where_str)
        devs = self.get_devices_where(where_str)
        logging.info(str(len(devs)) + " devices")
        for dev in devs:
            logging.info("Deleting " + str(dev["$urn"]))
            resp = requests.delete(self.url + dev["$urn"], headers=set_headers(self.key))
            if not resp.ok:
                logging.error(str(resp.reason) + ":" + str(resp.text))

    def get_devices(self):
        logging.info("Loading all devices")
        r = self.url + '/devices'
        resp = requests.get(r, headers=set_headers(self.key))
        devices = json.loads(resp.text)
        logging.info("Loaded " + str(len(devices)) + " devices")
        # Remove all DevicePilot-internal properties
        for device in devices:
            for propName in dict(device):
                if (propName.startswith("$") and propName not in ["$ts", "$id"]) or propName.endswith("State"):
                    del device[propName]
        return devices

    def get_devices_where(self, where):  # where could be e.g. '(State == "LIVE_OCCUPIED")'
        r = self.url + '/devices?$profile=/profiles/$view&where=' + urllib.quote_plus(where)
        resp = requests.get(r, headers=set_headers(self.key))
        return json.loads(resp.text)

    def get_device_history(self, device_urn, start, end, fields):
        req = self.url + device_urn + "/history" + "?" + urllib.urlencode(
            {"start": start, "end": end, "fields": fields}) + "&timezoneOffset=0" + "&random=973"
        resp = requests.get(req, headers=set_headers(
            self.key))  # Beware caching of live data (change 'random' value to avoid)
        if not resp.ok:
            logging.error(str(resp.reason))
            logging.error(str(resp.text))
        return json.loads(resp.text)

    def create_filter(self, name, spec):
        # spec could be "$ts < ago(86400)"
        # Returns the $id value of the new filter
        url = self.url + "/savedSearches"
        body = json.dumps({"$description": name, "where": spec})
        logging.info("createFilter " + str(body))
        resp = requests.post(url, verify=True, headers=set_headers(self.key),
                             data=body)  # Will only replace any existing one if $id is provided
        if not resp.ok:
            logging.error("createFilter:" + str(resp))
            return None
        the_id = json.loads(resp.text)["$id"]
        logging.info("Created filter with id " + str(the_id))
        return the_id

    def create_incident_config(self, filter_id, active=True):
        url = self.url + "/incidentConfigs"
        body = json.dumps({"$savedSearch": filter_id, "active": active})
        logging.info("createIncidentConfig " + str(body))
        resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)
        if not resp.ok:
            logging.error("createIncidentConfig:" + str(resp))
            return None
        the_id = json.loads(resp.text)["$id"]
        logging.info("Created incidentConfig with id " + str(the_id))
        return the_id

    def setup_demo_filters(self):  # Very specific set of filters and processes
        f_id = self.create_filter("Down (demo)", "$ts < ago(86400)")
        self.create_incident_config(f_id)  # Add monitoring to this filter
