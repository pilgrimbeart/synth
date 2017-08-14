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

import logging, time
import json, requests, httplib, urllib
from clients.client import Client

lastPostTime = 0

logging.getLogger("requests").setLevel(logging.WARNING) # Suppress annoying connection messages from Requests

def set_headers(token):
    headers = {}
    headers["Authorization"] = "Token {0}".format(token)
    headers["Content-Type"] = "application/json"
    return headers

class Devicepilot(Client):
    def __init__(self, params):
        logging.info("Initialising DevicePilot client")
        self.url = params["devicepilot_api"]
        self.key = params["devicepilot_key"]
        self.queueFlushCriterion = params.get("queue_criterion","messages") # or "time" or "interactive"
        self.queueFlushLimit = params.get("queue_limit",500)
        # queue_criterion/limit sets how often we flush messages to DevicePilot API
        # If criterion=="messages" then limit is number of messages, e.g. 1000
        # If criterion=="time" then limit is amount of simulated time passing, e.g. sim.days(30)
        # If criterion=="interactive" then limit is amount of real time passing, e.g. 1 (second)
        if "setup_demo_filters" in params:
            self.setupDemoFilters()

        self.postQueue = []
        self.postCount = 0

    def add_device(self, device_id, time, properties):
        self.update_device(device_id, time, properties)
        pass
    
    def update_device(self, device_id, time, properties):
        props = properties.copy()
        props.update({"$id" : device_id, "$ts" : time})
        self.postQueue.append(props)
        self.flushPostQueueIfReady()

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        logging.info("DevicePilot client entering (interactive,1sec) mode")
        self.flushPostQueue()
        # self.recalcHistorical(anId)
        self.queueFlushCriterion = "interactive"
        self.queueFlushLimit = 1
    
    def flush(self):
        self.flushPostQueue()
        # self.recalcHistorical(device.devices[0].properties["$id"])  # Nasty hack, need any old id in order to make a valid post
        logging.info("A total of "+str(self.postCount)+" items were posted to DevicePilot")

    def tick(self):
        self.flushPostQueueIfReady()
        

    def postDevice(self, device, historical=False):
        # DevicePilot API accepts either a single JSON object, or an array of such
        # If <historical> is true, DevicePilot doesn't calculate any dependent events (so e.g. won't send alerts)
        global lastPostTime
        lastPostTime = time.time()
        
        body = json.dumps(device)
        
        if isinstance(device, list):
            self.postCount += len(device)
        else:
            self.postCount += 1

        try:
            url = self.url
            if historical:
                url += '/ingest'    # Was to "/historical"
            else:
                url += '/ingest'
            resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)
        except httplib.HTTPException as err:
            logging.error("ERROR: devicepilot.postDevice() couldn't create on server")
            logging.error(str(err))
            logging.error(str(device))

        if resp.status_code == 207: # Multi-response
            for i in json.loads(resp.text):
                if (i["status"] < 200) or (i["status"] > 299):
                    logging.error("ERROR:"+str(i))
        else:
            if resp.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logging.error("devicepilot.PostDevice() couldn't create on server")
                # print  '%(status)03d (%(text)s)' % {"status": resp.status_code, "text": httplib.responses[resp.status_code]}
                logging.error("URL:"+str(url))
                logging.error("Status code:"+str(resp.status_code))
                logging.error("Text:"+str(resp.text))
                logging.error("Body:"+str(body))

        return True

    def readyToFlush(self):
        if self.queueFlushCriterion == "messages":
            if len(self.postQueue) >= self.queueFlushLimit:
                return True
        if self.queueFlushCriterion == "time":
            # Note that $ts properties in the post queue will be in epoch-MILLIseconds as that's what DP expects
            if self.postQueue[-1]["$ts"] - self.postQueue[0]["$ts"] >= self.queueFlushLimit * 1000:
                return True
        if self.queueFlushCriterion == "interactive":
            if time.time() - lastPostTime > self.queueFlushLimit:
                return True
        return False

    def flushPostQueueIfReady(self):
        if self.readyToFlush():
            self.flushPostQueue()

    def flushPostQueue(self):
        if len(self.postQueue) > 0:
            logging.info("POSTing "+str(len(self.postQueue))+" queued items into DevicePilot")
            self.postDevice(self.postQueue, historical=True)
            self.postQueue = []

    def recalcHistorical(self, anId):
        logging.info("DevicePilot client finalising historical updates")
        self.postDevice({"$id" : anId}, historical=False) # After a run of historical posts, posting anything with (historical==False) triggers DevicePilot to update all its event calculations [we just need any valid id]
        resp = requests.put(self.url + '/propertySummaries', headers=set_headers(self.key)) # Tell DP that we should regen property summaries
        
    def deleteAllDevices(self):
        logging.info("Deleting all devices on this account...")
        resp = requests.delete(self.url + "/devices", headers=set_headers(self.key))
        logging.info("All devices deleted")

    def deleteDevicesWhere(self, whereStr): 
        logging.info("Deleting all devices where "+whereStr)
        devs = self.getDevicesWhere(whereStr)
        logging.info("    "+str(len(devs))+" devices to delete")
        for dev in devs:
            logging.info("Deleting "+str(dev["$urn"]))
            resp = requests.delete(self.url + dev["$urn"], headers=set_headers(self.key))
            if not resp.ok:
                logging.error(str(resp.reason) + ":" + str(resp.text))
        
    def getDevices(self):
        logging.info("Loading all devices")
        r = self.url + '/devices'
        resp = requests.get(r, headers=set_headers(self.key))
        devices = json.loads(resp.text)
        logging.info("    Loaded "+str(len(devices))+" devices")
        # Remove all DevicePilot-internal properties
        for device in devices:
            for propName in dict(device):
                if (propName.startswith("$") and propName not in ["$ts","$id"]) or propName.endswith("State"):
                    del device[propName]
        return devices

    def getDevicesWhere(self, where):   # where could be e.g. '(State == "LIVE_OCCUPIED")'
        r = self.url + '/devices?$profile=/profiles/$view&where=' + urllib.quote_plus(where)
        resp = requests.get(r, headers=set_headers(self.key))
        return json.loads(resp.text)

    def getDeviceHistory(self, deviceURN, start, end, fields):
        req = self.url + deviceURN + "/history" + "?" + urllib.urlencode({"start":start,"end":end,"fields":fields}) + "&timezoneOffset=0"+"&random=973"
        resp = requests.get(req, headers=set_headers(self.key))    # Beware caching of live data (change 'random' value to avoid)
        if not resp.ok:
            logging.error(str(resp.reason))
            logging.error(str(resp.text))
        return json.loads(resp.text)

    def createFilter(self, name, spec, monitor=False):
        """Create a DevicePilot filter and return the $id of the new filter.

           spec could be e.g. '$ts < ago(86400)'"""
        url = self.url + "/savedSearches"
        body = json.dumps({ "$description" : name, "where" : spec })
        logging.info("createFilter "+str(body))
        resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)    # Will only replace any existing one if $id is provided
        if not resp.ok:
            logging.error("createFilter:"+str(resp))
            return None
        theID = json.loads(resp.text)["$id"]
        logging.info("Created filter with id "+str(theID))
        return theID

    def createIncidentConfig(self, filterID, active=True):
        url = self.url + "/incidentConfigs"
        body = json.dumps({ "$savedSearch" : filterID, "active" : active })
        logging.info("createIncidentConfig "+str(body))
        resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)
        if not resp.ok:
            logging.error("createIncidentConfig:"+str(resp))
            return None
        theID = json.loads(resp.text)["$id"]
        logging.info("Created incidentConfig with id "+str(theID))
        return theID

    def setupDemoFilters(self):
        """Very specific set of filters and processes, to support zero-touch onboarding."""
        fID = self.createFilter("Down (demo)", "$ts < ago(86400)", True)
        iID = self.createIncidentConfig(fID)   # Add monitoring to this filter
