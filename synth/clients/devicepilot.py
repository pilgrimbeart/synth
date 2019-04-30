#!/usr/bin/env python
r"""
DevicePilot client
==================
This client posts event data into DevicePilot. It is also capable of doing historical bulk uploads and being interactive. It can also delete devices, create DevicePilot filters, events and actions.

To find your DevicePilot access key:

    1. Log on to your DevicePilot account
    2. Click Settings / My User and find your key in the API Key section


DevicePilot client specification
--------------------------------
The client accepts the following parameters (usually found in the "On*.json" file in ../synth_accounts)::

    "client" : {
        "type" : "devicepilot",
        "devicepilot_api" : "https://api.devicepilot.com",
        "devicepilot_key" : "xxxxxxxxxxxxxxxxxxxx", # Your key from DevicePilot Settings page
        "devicepilot_min_post_period" : "PT10S",    # Optional. Do not post more often than this.
        "devicepilot_max_items_per_post" : 500,     # Optional. Individual posts cannot be bigger than this (the DP /device endpoint has a 1MB payload limit per post)
        "devicepilot_mode" : "bulk|interactive",    # In bulk mode, events are written to DevicePilot in bulk. In interactive mode they are written one-by-one (this mode is entered automatically when real-time is reached)
        "aws_access_key_id" : "xxxxxxxxxxxxxxxx",   # Optional (AWS credential only required if you use bulk mode)
        "aws_secret_access_key" : "xxxxxxxxxxxxxxxxxxxxx",  # Ditto
        "aws_region" : "eu-west-1",                          # Ditto
        "merge_posts" : true    # Spots cases where different device properties are being updated at the same time (and therefore could be merged into a single post)
    }

DevicePilot client event actions
--------------------------------
If you're using the DevicePilot client then the following client-specific actions are available:

Create arbitrary DevicePilot filters::

    "action" :
    {
        "client.create_filters" : [
            {
                "$description" : "Down (test)",
                "where" : "$ts < ago(300)",
                "monitor" : true,
                "action" : {
                    "$description": "Notify Synth of timeout (test)",
                    "body": "{\n\"deviceId\" : \"{device.$id}\",\n\"eventName\" : \"notifyTimeout\"\n}",
                    "headers": {
                        "Instancename": "<<<instance_name>>>",
                        "Key": "<<<web_key>>>"
                    },
                    "method": "POST",
                    "target": "request",
                    "url": "https://synth.devicepilot.com/event"
                }
            }
        ]
    }

Delete all DevicePilot filters::

    "action" : { "client.delete_all_filters" : {} }

Synchronise with DevicePilot (i.e. wait until all data we've posted into DevicePilot has been ingested and is now available)::

    "action" : { "client.sync" : {} }

Query DevicePilot (you'll probably want to do a client.sync first). Parameters are passed straight through to the `/query` endpoint, so you can use all the combinations that that supports. ::

    "action": {
        "client.query" : {
            "start" : "2017-01-01T00:00:00",
            "end" : "2017-01-02T00:00:00",
            "op" : "duration",
            "valueFilterStr" : "$ts > ago(86400)",
            "expect" : { <optionally define this parameter to throw an error if the query result doesn't match> }
        }
    }

The DevicePilot client has two modes of pushing events into DevicePilot:

    * `bulk` mode generates JSON files locally, and then does a bulk-upload to DevicePilot (via AWS)
    * `interactive` mode send events directly into the /devices DevicePilot API (slower, but will trigger actions and is interactive)

The client defaults to `interactive` mode, and automatically changes to `interactive` mode either at the end of the simulation, or when real-time is reached, whichever comes first.
If you want to change to `interactive` mode within your simulation, you can use the "set_mode" command::

    "action" : {
        "set_mode" : "bulk|interactive"
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

import logging, time
import json
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import httplib, urllib
import isodate
import traceback
import boto3 # AWS library for bulk upload
from clients.client import Client
from common import ISO8601, top, json_writer, evt2csv

SAVEDSEARCH_ENDPOINT = "/savedSearches"         # UI calls these "filters"
INCIDENTCONFIG_ENDPOINT = "/incidentConfigs"    # UI calls these "event configurations"
NOTIFICATION_ENDPOINT = "/notifications"        # UI calls these "actions"
DEVICE_ENDPOINT = "/devices"
MAX_POST_SIZE_BYTES = 500000    # AWS ingestion limit is actually 1MB but even half of that is pretty massive

# Suppress annoying Requests debug
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests.auth").setLevel(logging.WARNING)
logging.getLogger("requests.packages").setLevel(logging.WARNING)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3.poolmanager").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

debug_post = False
debug_queue = False

merged_posts = 0

def set_headers(token):
    headers = {}
    headers["Authorization"] = "Token {0}".format(token)
    headers["Content-Type"] = "application/json"
    return headers

class Devicepilot(Client):
    def __init__(self, instance_name, context, params):
        """There are two types of queue-throttling:
            1) flush_criterion says "don't post until you have X messages (or X secs have passed)"
            2) throttle_seconds_per_post says "ensure X seconds between any post"
        """
        logging.info("Initialising DevicePilot client")
        self.instance_name = instance_name
        self.context = context
        self.params = params
        self.url = params["devicepilot_api"]
        self.key = params["devicepilot_key"]
        self.mode = params.get("devicepilot_mode", "interactive")  # Either "bulk" or "interactive"
        self.throttle_seconds_per_post = params.get("devicepilot_throttle_seconds_per_post", None)
        # self.queue_flush_criterion = params.get("queue_criterion","messages") # or "time" or "interactive"
        # self.queue_flush_limit = params.get("queue_limit",500)
        self.merge_posts = params.get("merge_posts", False)
        self.min_post_period = isodate.parse_duration(params.get("devicepilot_min_post_period", "PT10S")).total_seconds()
        self.max_items_per_post = params.get("devicepilot_max_items_per_post", 500)
        self.last_post_time = time.time() - self.min_post_period    # Allow first post immediately
        self.json_stream = json_writer.Stream(instance_name)
        self.top = top.top()

        # queue_criterion/limit sets how often we flush messages to DevicePilot API
        # If criterion=="messages" then limit is number of messages, e.g. 1000
        # If criterion=="time" then limit is amount of simulated time passing, e.g. sim.days(30)
        # If criterion=="interactive" then limit is amount of real time passing, e.g. 1 (second)

        self.post_queue = []
        self.post_count = 0

        self.session = requests.Session()   # Using a persistent session allows re-use of connection, retries 
        retries = Retry(total=5,
                backoff_factor=0.1,
                method_whitelist=['GET', 'POST'],    # By default Requests will not retry a POST (for idempotency reasons)
                status_forcelist=[ 104, 403 ])   # Connection occasionally gets closed. DevicePilot will throw occasional auth failures.
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def _send_update(self, device_id, time, properties, record):
        global merged_posts
        props = properties.copy()
        props.update({"$id" : device_id, "$ts" : time})
        self.top.update(props)
        if self.mode == "interactive":
            if self.merge_posts:
                if len(self.post_queue)>0:
                    if self.post_queue[-1]["$ts"] == props["$ts"]:
                        if self.post_queue[-1]["$id"] == props["$id"]:
                            merged_posts = merged_posts + 1
                            props.update(self.post_queue[-1])
                            del(self.post_queue[-1])
            self.post_queue.append(props)
            self.flush_post_queue_if_ready()
        if (self.mode == "bulk") and (record):
            self.json_stream.write_event(props)

    def add_device(self, device_id, time, properties):
## NOTE: DevicePilot API doesn't require a separate "create device" call (device is created automatically on first mention)
##       and sending an update here causes properties to be resent, potentially duplicating state which can invalidate tests
##        if debug_queue:
##            logging.info("devicepilot::add_device queueing "+str(properties))
##            traceback.print_stack()
##        self._send_update(device_id, time, properties, False)
        pass
    
    def update_device(self, device_id, time, properties):
        if debug_queue:
            logging.info("devicepilot::update_device queueing "+str(properties))
            traceback.print_stack()
        self._send_update(device_id, time, properties, True)

    def get_device(self, device_id):
        pass
    
    def get_devices(self):
        pass
    
    def delete_device(self, device_id):
        pass

    def enter_interactive(self):
        self.set_mode("interactive")

    def set_mode(self, mode):
        if self.mode == mode:
            return
        logging.info("DevicePilot client changing mode from "+str(self.mode)+" to "+str(mode))
        if mode=="interactive":
            self.flush_post_queue_if_ready()
            # self.recalcHistorical(anId)
            # self.queue_flush_criterion = "interactive"
            # self.queue_flush_limit = 1
            # self.min_post_period = 1
            self.bulk_upload()
            self.mode = "interactive"   # Must do this before we try to send top!
            self.send_top()
        self.mode = mode
        

    def bulk_upload(self):
        """Upload bulk data"""
        self.json_stream.close()    # Close off current file
        file_list = self.json_stream.files_written
        if len(file_list) == 0:
            logging.info("Nothing to bulk upload")
            return

        t = time.time()
        
        if "aws_access_key_id" in self.params:
##            print self.params.get("aws_access_key_id", None)
##            print self.params.get("aws_secret_access_key", None)
##            print self.params.get("aws_region", None)
            client = boto3.client('lambda',
                        aws_access_key_id=self.params.get("aws_access_key_id", None),
                        aws_secret_access_key=self.params.get("aws_secret_access_key", None),
                        region_name=self.params.get("aws_region", None))
        else:
            logging.info("bulk_upload: No AWS credentials supplied so using defaults")
            client = boto3.client('lambda')

        token = 'Token '+self.key

        total_events = 0
        for count, file_name in enumerate(file_list):
            logging.info("Bulk uploading "+file_name+" ("+str(count+1)+"/"+str(len(file_list))+")")
            points = json.load(open(file_name, "rt"))
            total_events += len(points)
            payload = json.dumps({ 
                'apiKey': token,
                'points': points,
                'last' : (count==len(file_list)-1)
            })
            # print "payload in:",payload
            response = client.invoke(
                FunctionName='api-digest-staging-inject',
                InvocationType='RequestResponse',
                Payload=payload,
                )
            ret = response['Payload'].read()
            assert ret=="{}", ret
        logging.info("Bulk upload completed (total of "+str(total_events)+" events at "+str(int(total_events / (time.time()-t)))+" events/s)")

    def send_top(self):
        """Send top (latest) value of all properties on all devices to the client"""
        logging.info("DevicePilot sending top values")
        for props in self.top.get():
            self.update_device(props["$id"], props["$ts"], props)

    def tick(self):
        self.flush_post_queue_if_ready()

    def close(self):
        logging.info("Closing DevicePilot client")
        if merged_posts > 0:
            logging.info("Saved "+str(merged_posts)+" posts by merging")
        self.json_stream.close()
        self.enter_interactive()    # Ensure that bulk uploads are done
        logging.info(str(len(self.post_queue))+" items to flush")
        while len(self.post_queue):
            self.flush_post_queue_if_ready()
            time.sleep(1)
        logging.info("A total of "+str(self.post_count)+" items were posted to DevicePilot")

    # Optional methods
    
    def delete_demo_devices(self):
        self.delete_devices_where('(is_demo_device == true)')        

    # Internal methods
    
    def _post_device(self, device, historical):
        # DevicePilot API accepts either a single JSON object, or an array of such
        # If <historical> is true, DevicePilot doesn't calculate any dependent events (so e.g. won't send alerts)
        self.last_post_time = time.time()

        body = json.dumps(device)

        # logging.info(body)
        
        if isinstance(device, list):
            self.post_count += len(device)
        else:
            self.post_count += 1

        try:
            url = self.url
            if historical:
                url += DEVICE_ENDPOINT    # Was to "/historical"
            else:
                url += DEVICE_ENDPOINT
            resp = self.session.post(url, verify=True, headers=set_headers(self.key), data=body)
            if debug_post:
                logging.info("devicePilot::post_device posted "+str(body))
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


    def post_device(self, device, historical=False):
        if not isinstance(device, list):
            return self._post_device(device, historical)
        D = device[:]
        while len(D) > 0:  # Break into small-enough chunks 
            L = []
            while len(D) > 0:
                if len(str(L)+str(D[0])) > MAX_POST_SIZE_BYTES: # Keep going until we break the size barrier
                    logging.info("Breaking-up too-large post")
                    break
                L.append(D[0])
                del(D[0])
            self._post_device(L, historical)

        return True

    def how_many_to_flush(self):
        """Return number of items to flush"""
##        num = 0
##        if self.queue_flush_criterion == "messages":
##            if len(self.post_queue) >= self.queue_flush_limit:
##                num = None
##        if self.queue_flush_criterion == "time":
##            # Note that $ts properties in the post queue will be in epoch-MILLIseconds as that's what DP expects
##            if self.post_queue[-1]["$ts"] - self.post_queue[0]["$ts"] >= self.queue_flush_limit * 1000:
##                num = None
##        if self.queue_flush_criterion == "interactive":
##            if time.time() - self.last_post_time > self.queue_flush_limit:
##                num = None

        if time.time() - self.last_post_time < self.min_post_period:
            return 0
        return min(len(self.post_queue), self.max_items_per_post)

##        if self.throttle_seconds_per_post is not None:
##            if num == None:
##                num = int((time.time() - self.last_post_time) / self.throttle_seconds_per_post)
##                time.sleep(1)   # TODO: Horrid, but without this we'll do loads of back-to-back posts
##        return num

    def flush_post_queue_if_ready(self):
        num_items = self.how_many_to_flush()
        if num_items > 0:
            self.flush_post_queue(num_items)

    def flush_post_queue(self, max_items=None):
        if len(self.post_queue) > 0:
            limit = len(self.post_queue)
            comment = ""
            if max_items is not None:
                limit = max_items
                if limit < len(self.post_queue):
                    comment = " ("+str(len(self.post_queue)-limit)+" throttled)"
            logging.info("POSTing "+str(limit)+" queued items into DevicePilot" + comment)
            self.post_device(self.post_queue[0:limit], historical=True)
            self.post_queue = self.post_queue[limit:]

    def recalc_historical(self, anId):
        logging.info("DevicePilot client finalising historical updates")
        self.post_device({"$id" : anId}, historical=False) # After a run of historical posts, posting anything with (historical==False) triggers DevicePilot to update all its event calculations [we just need any valid id]
        resp = self.session.put(self.url + '/propertySummaries', headers=set_headers(self.key)) # Tell DP that we should regen property summaries
        
    def delete_all_devices(self):
        assert ("api-staging" in self.url) or ("api-development" in self.url), "Refusing to delete all devices, because "+self.url+" is not a development/staging account"

        logging.info("Deleting all devices on this account")
        for i in range(3):
            resp = self.session.delete(self.url + "/devices", headers=set_headers(self.key))
            if resp.ok:
                break
            else:
                logging.warning("Delete returned an error (not unusual, so retrying) "+str(resp.reason) + " : " + str(resp.text))
        assert resp.ok, resp.reason + " : " + resp.text
        logging.info("All devices deleted")

        logging.info("Deleting all device properties on this account")
        resp = self.session.delete(self.url + "/properties", headers=set_headers(self.key))
        assert resp.ok, resp.reason + " : " + resp.text
        logging.info("All device properties deleted")

    def delete_devices_where(self, whereStr, suppress_log_messages = False): 
        if not suppress_log_messages:
            logging.info("Deleting all devices where "+whereStr)
        devs = self.get_devices_where(whereStr)
        if not suppress_log_messages:
            logging.info("    "+str(len(devs))+" devices to delete")
        for dev in devs:
            if not suppress_log_messages:
                logging.info("Deleting "+str(dev["$urn"]))
            resp = self.session.delete(self.url + dev["$urn"], headers=set_headers(self.key))
            if not resp.ok:
                logging.error(str(resp.reason) + ":" + str(resp.text))

##    def get_devices(self):
##        logging.info("Loading all devices")
##        r = self.url + '/devices'
##        resp = self.session.get(r, headers=set_headers(self.key))
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
        resp = self.session.get(r, headers=set_headers(self.key))
        return json.loads(resp.text)

##    def get_device_history(self, device_URN, start, end, fields):
##        req = self.url + device_URN + "/history" + "?" + urllib.urlencode({"start":start,"end":end,"fields":fields}) + "&timezoneOffset=0"+"&random=973"
##        resp = self.session.get(req, headers=set_headers(self.key))    # Beware caching of live data (change 'random' value to avoid)
##        if not resp.ok:
##            logging.error(str(resp.reason))
##            logging.error(str(resp.text))
##        return json.loads(resp.text)

    def get_device_history(self, device_id, start, end, fields):
        req = self.url + "/query?last"
        query = {
            "op":"history",
            "start" : start,
            "end" : end,
            "select": {
                "deviceId" : device_id,
                "fields" : fields
                }
            }
        resp = self.session.post(req, headers=set_headers(self.key), data=json.dumps(query))
        assert resp.ok, "Problem getting device history "+json.dumps(query)+"\n"+resp.text
        return json.loads(resp.text)
        
    def get_all_X(self, endpoint):
        """Return all X (where X is some DevicePilot endpoint such as "/savedSearches")"""
        return json.loads(self.session.get(self.url + endpoint, headers=set_headers(self.key)).text)
        
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

        url = self.url + endpoint
        resp = self.session.post(url, verify=True, headers=set_headers(self.key), data=json.dumps(body_set))
        if debug_post:
            logging.info("devicePilot::create_or_update_X posted "+str(body_set))
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
        the_id = self.get_X_id_by_field(INCIDENTCONFIG_ENDPOINT, "$savedSearch", filter_id)
        if the_id is not None:
            resp = self.session.delete(self.url + the_id, headers=set_headers(self.key))

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
        the_id = self.get_X_id_by_field(NOTIFICATION_ENDPOINT, "$description", action["$description"])
        if the_id is not None:
            resp = self.session.delete(self.url + the_id, headers=set_headers(self.key))

        body_set = action
        return self.create_or_update_X(NOTIFICATION_ENDPOINT, "$description", action["$description"], body_set)

    # PLUG-IN ACTIONS

    def PLUGIN_create_filters(self, filters):
        """Create arbitrary DevicePilot filters"""
##        print "/savedSearches (aka Filters):"
##        print json.dumps(self.get_all_X(SAVEDSEARCH_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
##        print "/incidentConfigs (aka Events):"
##        print json.dumps(self.get_all_X(INCIDENTCONFIG_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
##        print "/notifications (aka: Actions)"
##        print json.dumps(self.get_all_X(NOTIFICATION_ENDPOINT), indent=4, sort_keys=True, separators=(',', ': '))
        
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

    def PLUGIN_delete_all_filters(self, _):
        logging.info("Deleting all DevicePilot filters")
        # (we could probably just do a single delete of /savedSearches endpoint instead of deleting one-by-one)
        filters = self.get_all_X(SAVEDSEARCH_ENDPOINT)
        for F in filters:
            logging.info("Deleting filter "+F["$description"])
            resp = self.session.delete(self.url + F["$id"], headers=set_headers(self.key))
            assert resp.ok, str(resp.reason) + str(resp.text)

    def PLUGIN_query(self, params):
        body = {}
        for p in params:
            if p in ["expect"]:
                pass
            elif p in ["start","end"]:
                body.update({p : ISO8601.to_epoch_seconds(params[p])*1000}),   # TODO: Needs * 1000 for ms?
            else:
                body.update({p : params[p]})
        logging.info("DevicePilot query:\n"+json.dumps(body, sort_keys=True, indent=4, separators=(',', ': ')))
        resp = self.session.post(self.url+"/query", verify=True, headers=set_headers(self.key), data=json.dumps(body))
        assert resp.ok, str(resp.reason) + str(resp.text)
        result = json.loads(resp.text)
        logging.info("Query returned:\n"+json.dumps(result, sort_keys=True, indent=4, separators=(',', ': ')))

        if "expect" in params:
            expected = params["expect"]
            if result == expected:
                logging.info("Query returned expected result - PASS")
            else:
                logging.info("Expected result:\n"+json.dumps(expected, sort_keys=True, indent=4, separators=(',', ': ')))
                assert False, "Query did not return expected result - FAIL"

    def PLUGIN_set_mode(self, mode):
        self.set_mode(mode)

    def PLUGIN_sync(self, _):
        """Synchronise Synth with DevicePilot (i.e. wait until data in Synth is consistent)"""
        logging.info("Synchronising with DevicePilot")
        self.set_mode("interactive")

        t = time.time()
        device_id = "SyncDevice"+str(int(t))
        self.add_device(device_id, t, properties={})
        where_str = '($id == \"'+device_id+'")'
        while True:
            self.flush_post_queue_if_ready()
            devs = self.get_devices_where(where_str)
            if devs != []:
                break
            logging.info("Waiting to sync (waited " + str(int(time.time()-t)) + "s so far)")
            time.sleep(10)
        self.delete_devices_where(where_str, suppress_log_messages=True)
        logging.info("Synchronised with DevicePilot")

    def PLUGIN_DELETE_ALL_DEVICES(self, _):
        """Delete all devices DevicePilot. We use an uppercase name to make it more obvious in scenario files! """
        self.delete_all_devices()

    def PLUGIN_fetch_history(self, params):
        # start = time.time() + isodate.parse_duration(params.get("start", "-P7D")).total_seconds()
        # end = time.time() + isodate.parse_duration(params.get("start", "PT0S")).total_seconds()
        start = params["start"]
        end = params["end"]
        devices = self.get_all_X(DEVICE_ENDPOINT)
        filename = "../synth_logs/"+self.instance_name+"_history"
        json_file = open(filename+".json","wt") # Do this to discover problems (e.g. open editor) before our expensive operations
        csv_file = open(filename+".csv","wt")
        
        evts = {}
        for count, d in enumerate(devices):
            try:    # Don't let very occasional fetch error kill a long process
                logging.info("Fetching history for device "+str(d["$id"])+" ("+str(count)+" of "+str(len(devices))+")")
                fields = [x for x in d.keys() if not x.startswith("$ts/")]
                history = self.get_device_history(d["$id"], start, end, fields)
                evt_count = 0
                for evt in history:
                    evt["$id"] = d["$id"]
                    evt["$ts"] = evt["$ts"] / 1000.0    # Convert from ms to s
                    if len(evt) > 2:    # Suppress empty timestamps 
                        evt2csv.insert_properties(evts, evt)
                        evt_count+=1
                logging.info(str(evt_count)+" events")
            except:
                logging.error(traceback.format_exc())
        logging.info("Writing "+filename+".json")
        evt2csv.write_as_json(evts, filename+".json")
        logging.info("Writing "+filename+".csv")
        csv = evt2csv.convert_to_csv(evts)
        csv_file.write(csv)
