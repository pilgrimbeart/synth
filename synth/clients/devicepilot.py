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

SAVEDSEARCH_ENDPOINT = "/savedSearches"         # UI calls these "filters"
INCIDENTCONFIG_ENDPOINT = "/incidentConfigs"    # UI calls these "event configurations"
NOTIFICATION_ENDPOINT = "/notifications"        # UI calls these "actions"

last_post_time = 0

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
        self.queue_flush_criterion = params.get("queue_criterion","messages") # or "time" or "interactive"
        self.queue_flush_limit = params.get("queue_limit",500)
        # queue_criterion/limit sets how often we flush messages to DevicePilot API
        # If criterion=="messages" then limit is number of messages, e.g. 1000
        # If criterion=="time" then limit is amount of simulated time passing, e.g. sim.days(30)
        # If criterion=="interactive" then limit is amount of real time passing, e.g. 1 (second)
        if "create_devicepilot_filters" in params:
            self.setup_filters(params["create_devicepilot_filters"])

        self.post_queue = []
        self.post_count = 0

    def add_device(self, device_id, time, properties):
        self.update_device(device_id, time, properties)
        pass
    
    def update_device(self, device_id, time, properties):
        props = properties.copy()
        props.update({"$id" : device_id, "$ts" : time})
        self.post_queue.append(props)
        self.flush_post_queue_if_ready()

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        logging.info("DevicePilot client entering (interactive,1sec) mode")
        self.flush_post_queue()
        # self.recalcHistorical(anId)
        self.queue_flush_criterion = "interactive"
        self.queue_flush_limit = 1
    
    def flush(self):
        self.flush_post_queue()
        # self.recalcHistorical(device.devices[0].properties["$id"])  # Nasty hack, need any old id in order to make a valid post
        logging.info("A total of "+str(self.post_count)+" items were posted to DevicePilot")

    def tick(self):
        self.flush_post_queue_if_ready()

    # Optional methods
    
    def delete_demo_devices(self):
        self.delete_devices_where('(is_demo_device == true)')        

    # Internal methods
    
    def post_device(self, device, historical=False):
        # DevicePilot API accepts either a single JSON object, or an array of such
        # If <historical> is true, DevicePilot doesn't calculate any dependent events (so e.g. won't send alerts)
        global last_post_time
        last_post_time = time.time()
        
        body = json.dumps(device)
        
        if isinstance(device, list):
            self.post_count += len(device)
        else:
            self.post_count += 1

        try:
            url = self.url
            if historical:
                url += '/ingest'    # Was to "/historical"
            else:
                url += '/ingest'
            resp = requests.post(url, verify=True, headers=set_headers(self.key), data=body)
        except httplib.HTTPException as err:
            logging.error("ERROR: devicepilot.post_device() couldn't create on server")
            logging.error(str(err))
            logging.error(str(device))

        if resp.status_code == 207: # Multi-response
            for i in json.loads(resp.text):
                if (i["status"] < 200) or (i["status"] > 299):
                    logging.error("ERROR:"+str(i))
        else:
            if resp.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logging.error("devicepilot.post_device() couldn't create on server")
                # print  '%(status)03d (%(text)s)' % {"status": resp.status_code, "text": httplib.responses[resp.status_code]}
                logging.error("URL:"+str(url))
                logging.error("Status code:"+str(resp.status_code))
                logging.error("Text:"+str(resp.text))
                logging.error("Body:"+str(body))

        return True

    def ready_to_flush(self):
        if self.queue_flush_criterion == "messages":
            if len(self.post_queue) >= self.queue_flush_limit:
                return True
        if self.queue_flush_criterion == "time":
            # Note that $ts properties in the post queue will be in epoch-MILLIseconds as that's what DP expects
            if self.post_queue[-1]["$ts"] - self.post_queue[0]["$ts"] >= self.queue_flush_limit * 1000:
                return True
        if self.queue_flush_criterion == "interactive":
            if time.time() - last_post_time > self.queue_flush_limit:
                return True
        return False

    def flush_post_queue_if_ready(self):
        if self.ready_to_flush():
            self.flush_post_queue()

    def flush_post_queue(self):
        if len(self.post_queue) > 0:
            logging.info("POSTing "+str(len(self.post_queue))+" queued items into DevicePilot")
            self.post_device(self.post_queue, historical=True)
            self.post_queue = []

    def recalc_historical(self, anId):
        logging.info("DevicePilot client finalising historical updates")
        self.post_device({"$id" : anId}, historical=False) # After a run of historical posts, posting anything with (historical==False) triggers DevicePilot to update all its event calculations [we just need any valid id]
        resp = requests.put(self.url + '/propertySummaries', headers=set_headers(self.key)) # Tell DP that we should regen property summaries
        
    def delete_all_devices(self):
        logging.info("Deleting all devices on this account...")
        resp = requests.delete(self.url + "/devices", headers=set_headers(self.key))
        logging.info("All devices deleted")

    def delete_devices_where(self, whereStr): 
        logging.info("Deleting all devices where "+whereStr)
        devs = self.get_devices_where(whereStr)
        logging.info("    "+str(len(devs))+" devices to delete")
        for dev in devs:
            logging.info("Deleting "+str(dev["$urn"]))
            resp = requests.delete(self.url + dev["$urn"], headers=set_headers(self.key))
            if not resp.ok:
                logging.error(str(resp.reason) + ":" + str(resp.text))

##    def get_devices(self):
##        logging.info("Loading all devices")
##        r = self.url + '/devices'
##        resp = requests.get(r, headers=set_headers(self.key))
##        devices = json.loads(resp.text)
##        logging.info("    Loaded "+str(len(devices))+" devices")
##        # Remove all DevicePilot-internal properties
##        for device in devices:
##            for propName in dict(device):
##                if (propName.startswith("$") and propName not in ["$ts","$id"]) or propName.endswith("State"):
##                    del device[propName]
##        return devices

    def get_devices_where(self, where):   # where could be e.g. '(State == "LIVE_OCCUPIED")'
        r = self.url + '/devices?$profile=/profiles/$view&where=' + urllib.quote_plus(where)
        resp = requests.get(r, headers=set_headers(self.key))
        return json.loads(resp.text)

    def get_device_history(self, device_URN, start, end, fields):
        req = self.url + device_URN + "/history" + "?" + urllib.urlencode({"start":start,"end":end,"fields":fields}) + "&timezoneOffset=0"+"&random=973"
        resp = requests.get(req, headers=set_headers(self.key))    # Beware caching of live data (change 'random' value to avoid)
        if not resp.ok:
            logging.error(str(resp.reason))
            logging.error(str(resp.text))
        return json.loads(resp.text)

    def get_all_X(self, endpoint):
        """Return all X (where X is some DevicePilot endpoint such as "/savedSearches")"""
        return json.loads(requests.get(self.url + endpoint, headers=set_headers(self.key)).text)
        
    def get_X_id_by_field(self, endpoint, field, field_value):
        """Return the ID of an endpoint (e.g. a filter, if the endpoint is "/savedSearches") by value of some field, else None"""
        for f in self.get_all_X(endpoint):
            if f[field]==field_value:
                return f["$id"]
        return None

    def create_or_update_X(self, endpoint, field, field_value, body_set):
        """ Create something (e.g. a filter). Returns $id field."""
        the_id = self.get_X_id_by_field(endpoint, field, field_value)
        if the_id is not None:
            logging.info("("+endpoint+" already exists, so updating it)")
            body_set["$id"]=the_id      # POST will replace existing one iff $id is provided"""

        print "BODY=",body_set
        
        url = self.url + endpoint
        resp = requests.post(url, verify=True, headers=set_headers(self.key), data=json.dumps(body_set))
        if not resp.ok:
            logging.error(resp.text)
            resp.raise_for_status()
        the_id = json.loads(resp.text)["$id"]
        return the_id
        
    def create_filter(self, description, where):
        """Create a DevicePilot filter and return the $id of the new filter."""
        logging.info("devicepilot:create_filter("+str(description)+","+str(where)+")")
        body_set = { "$description" : description, "where" : where }
        return self.create_or_update_X(SAVEDSEARCH_ENDPOINT, "$description", description, body_set)

    def create_incidentconfig(self, filter_id, notification_id, active=True):
        """Create a DevicePilot incidentConfig and return its $id. Replaces if already exists."""
        logging.info("devicepilot:create_incidentconfig("+str(filter_id)+","+str(active)+")")

        ## BODGE TO AVOID 500 SERVER ERROR
        logging.info("deleting incidentconfig [BODGE to avoid 500 errors]")
        the_id = self.get_X_id_by_field(INCIDENTCONFIG_ENDPOINT, "$savedSearch", filter_id)
        logging.info("Existing id is "+str(the_id))
        if the_id is not None:
            resp = requests.delete(self.url + the_id, headers=set_headers(self.key))
            print "Delete response was ",resp

        body_set = { "$savedSearch" : filter_id,
                     "active" : active,
                     "$clearedNotifications" : [],
                     "$flaggedNotifications" : [notification_id]
                     }
        return self.create_or_update_X(INCIDENTCONFIG_ENDPOINT, "$savedSearch", filter_id, body_set)

    def create_notification(self, action):
        """Create a DevicePilot notification and return its $id. Replaces if already exists."""
        logging.info("devicepilot:create_notification("+str(action)+")")

        ## BODGE TO AVOID 500 SERVER ERROR
        logging.info("deleting notification [BODGE to avoid 500 errors]")
        the_id = self.get_X_id_by_field(NOTIFICATION_ENDPOINT, "$description", action["$description"])
        logging.info("Existing id is "+str(the_id))
        if the_id is not None:
            resp = requests.delete(self.url + the_id, headers=set_headers(self.key))
            print "Delete response was ",resp

        body_set = action
        return self.create_or_update_X(NOTIFICATION_ENDPOINT, "$description", action["$description"], body_set)

    def setup_filters(self, filters):
        """Create arbitrary DevicePilot filters"""
        print "/savedSearches (aka Filters):"
        print json.dumps(self.get_all_X(SAVEDSEARCH_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
        print "/incidentConfigs (aka Events):"
        print json.dumps(self.get_all_X(INCIDENTCONFIG_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
        print "/notifications (aka: Actions)"
        print json.dumps(self.get_all_X(NOTIFICATION_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
        
        for f in filters:
            description = f["$description"]
            where = f["where"]
            monitor = f.get("monitor",False)
            action = f.get("action",None)
            filter_ID = self.create_filter(description, where)
            if action is not None:
                notification_ID = self.create_notification(action)    # Add notification to this monitor
            if monitor or (action is not None):
                incident_ID = self.create_incidentconfig(filter_ID, notification_ID)   # When filter matches, do the action
