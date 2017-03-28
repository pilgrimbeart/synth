#!/usr/bin/env python

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

last_post_time = 0

logging.getLogger("requests").setLevel(logging.WARNING)  # Suppress annoying connection messages from Requests


def set_headers(token):
    headers = {"Authorization": "Token {0}".format(token), "Content-Type": "application/json"}
    return headers


class Api:
    """DevicePilot client library for synth."""

    def __init__(self, api_key=None, url="http://api.devcepilot.com"):
        """Return an instance of the DevicePilot synth client library.
        
        Args:
            api_key (str):
                API key authenticated to create devices on your DevicePilot account.
                See: https://app.devicepilot.com/#/settings
            url (str, optional):
                DevicePilot api url.
        
        Returns:
            Api: Configured DevicePilot API client.

        """
        logging.info("Initialising DevicePilot client")
        self.url = url
        self.api_key = api_key

        self.post_queue = []
        self.queue_criterion = "messages"  # or "time" or "interactive"
        self.queue_limit = 1000
        self.post_count = 0

    def set_queue_flush(self, criterion="messages", limit=1000):
        """Sets the queue flush mode.
        
        Args:
            criterion (str):
                The queue flush mode to use when working with the DevicePilot API.
                
                * `messages`: flush when number of messages reaches `limit`, e.g. 1000.
                * `time`: flush once the amount of simulated time passes `limit`, e.g. sim.days(30)
                * `interactive`: flush once the amount of real time has passed `limit`, e.g. 1 (second)
            limit (int): Matchig `limit` for the specified `criterion`.
             
        """
        self.queue_criterion = criterion
        self.queue_limit = limit

    def post_device(self, devices):
        """Updates a device state (or collection of) on DevicePilot.
        
        Requests to DevicePilot are throttled, see `set_queue_flush` for options.
        
        Args:
            devices (dict):
                Either a single, or array, of JSON objects representing the devices to update.
                See https://app-development.devicepilot.com/#/tutorial/devices for conventions.

        """
        if isinstance(devices, list):
            for device in devices:
                if device["$id"] == "device0":  # skip magic device id.
                    pass
                self.post_queue.extend(device.copy())
        else:
            if devices["$id"] == "device0":
                pass
            self.post_queue.append(devices.copy())

        self.flush_post_queue_if_ready()

    def __post_device(self, device, historical=False):  # Private to enforce throttling of api.
        """Update a device state (or collection of) on DevicePilot.
        
        Args:
            device (dict[]): Either a single, or array, of JSON objects representing the devices to update.
            historical (bool): If True, prvent calculate any dependent events (so e.g. won't send alerts)
        
        Returns:
            bool: True if post was successful.
        """
        global last_post_time
        last_post_time = time.time()

        body = json.dumps(device)

        if isinstance(device, list):
            self.post_count += len(device)
        else:
            self.post_count += 1

        try:
            url = self.url + '/devices'
            if historical:
                url = url + "?historical=true"
            response = requests.post(url, verify=True, headers=set_headers(self.api_key), data=body)
        except httplib.HTTPException as err:
            logging.error("devicepilot.postDevice() couldn't create on server")
            logging.error(str(err))
            logging.error(str(device))
            return False

        if response.status_code == 207:  # Multi-response
            for i in json.loads(response.text):
                if (i["status"] < 200) or (i["status"] > 299):
                    logging.error("ERROR:" + str(i))
                    return False
        else:
            if response.status_code != requests.codes.ok and response.status_code != requests.codes.created:
                logging.error("devicepilot.PostDevice() couldn't create on server")
                logging.error("Status code:" + str(response.status_code))
                logging.error("Text:" + str(response.text))
                logging.error("Body:" + str(body))
                return False

        return True

    def flush_post_queue_if_ready(self):
        """Posts queued API requests if throttle is met."""
        if self.ready_to_flush():
            self.flush_post_queue()

    def ready_to_flush(self):
        """Returns True if throttled queue is ready to flush."""
        if self.queue_criterion == "messages":
            if len(self.post_queue) >= self.queue_limit:
                return True
        if self.queue_criterion == "time":
            # Note that $ts properties in the post queue will be in epoch-MILLI seconds.
            if (self.post_queue[-1]["$ts"] - self.post_queue[0]["$ts"]) >= (self.queue_limit * 1000):
                return True
        if self.queue_criterion == "interactive":
            if time.time() - last_post_time > self.queue_limit:
                return True
        return False

    def flush_post_queue(self):
        """Posts queued API requests regardless of throttle criterion.
        
        DevicePilot API requests should be throttled; use this only prior to closing an instace.
        """
        if len(self.post_queue) > 0:
            logging.info("POSTing " + str(len(self.post_queue)) + " queued items into DevicePilot")
            self.__post_device(self.post_queue, historical=True)
            self.post_queue = []

    def recalc_historical(self, an_id):
        """Recalculate events following a historical (batch) post.
        
        After a run of historical posts, posting anything with (historical==False)
        triggers DevicePilot to update all its event calculations [we just need any valid id]
        
        Args:
            an_id (str): An existing device id.
        """
        logging.info("DevicePilot client finalising historical updates")
        self.__post_device({"$id": an_id}, historical=False)

        # Tell DP that we should regen property summaries
        assert requests.put(self.url + '/propertySummaries',
                            headers=set_headers(self.api_key)).status_code == 200

    def enter_interactive(self, an_id=None):
        """Switch API throttling settings to interactive mode.
        
        Args:
            an_id (str, optional): An existing device id (required to update after a historial/batch post).
        """
        logging.info("DevicePilot client entering (interactive,1sec) mode")
        if an_id:
            self.recalc_historical(an_id)
        self.queue_criterion = "interactive"
        self.queue_limit = 1

    def get_devices(self):
        """Get's all the devices in the user's DevicePilot account.
        
        Returns:
            [dict]: Array of devices with state.
        """
        logging.info("Loading all devices")
        response = requests.get(self.url + '/devices', headers=set_headers(self.api_key))
        devices = json.loads(response.text)
        logging.info("Loaded " + str(len(devices)) + " devices")
        # Strip all DevicePilot-internal properties
        for device in devices:
            for propName in dict(device):
                if (propName.startswith("$") and propName not in ["$ts", "$id"]) or propName.endswith("State"):
                    del device[propName]
        return devices

    def get_devices_where(self, where):
        """Gets all devices that match a criteria.
        
        Args:
            where (str):
                Filter criteria, see https://app-development.devicepilot.com/#/where for definition.
        
        Returns:
            [dict]: Array of devices with state.
            
        """
        r = self.url + '/devices?$profile=/profiles/$view&where=' + urllib.quote_plus(where)
        resp = requests.get(r, headers=set_headers(self.api_key))
        return json.loads(resp.text)

    def get_device_history(self, device_urn, start, end, fields):
        """Get the history of field changes for a device across an interval.
        
        Args:
            device_urn (str): DevicePilot URN of the device to fetch history of.
            start (str): ISO formatted start of interval.
            end (str): ISO formatted end of interval.
            fields ([str]): List of fields to report back.
        
        Returns:
            dict[]: Array of fields across history.
        
        """
        # Beware caching of live data (change 'random' value to avoid)
        query = urllib.urlencode({"start": start, "end": end, "fields": fields})
        nounce = "973"
        request = self.url + device_urn + "/history" + "?" + query + "&timezoneOffset=0" + "&random=" + nounce
        response = requests.get(request, headers=set_headers(self.api_key))
        if not response.ok:
            logging.error(str(response.reason))
            logging.error(str(response.text))
        return json.loads(response.text)

    def delete_all_devices(self):
        """Deletes all the account devices."""
        logging.info("Deleting all devices on this account...")
        assert requests.delete(self.url + "/devices", headers=set_headers(self.api_key)).status_code == 200
        logging.info("All devices deleted")

    def delete_devices_where(self, where):
        """Deletes all the account devices matching a specific criteria.
        
        Args:
            where (str): Filter criteria (see `get_devices_where`)
        
        Returns:
            bool: True if delete was succesful.
            
        """
        logging.info("Deleting all devices where " + where)
        devs = self.get_devices_where(where)
        logging.info(str(len(devs)) + " devices")
        for dev in devs:
            logging.info("Deleting " + str(dev["$urn"]))
            resp = requests.delete(self.url + dev["$urn"], headers=set_headers(self.api_key))
            if not resp.ok:
                logging.error(str(resp.reason) + ":" + str(resp.text))
                return False
            return True

    def create_filter(self, name, spec):
        """Create a device filter.
        
        Args:
            name (str): Name of filter to create.
            spec (str): Specification for filter (see `get_devices_where`)
        
        Returns:
            str: URN of the created filter (or None if unsuccessful.)

        """
        url = self.url + "/savedSearches"
        body = json.dumps({"$description": name, "where": spec})
        logging.info("createFilter " + str(body))
        response = requests.post(url, verify=True, headers=set_headers(self.api_key), data=body)
        if not response.ok:
            logging.error("createFilter:" + str(response))
            return None
        the_id = json.loads(response.text)["$id"]
        logging.info("Created filter with id " + str(the_id))
        return the_id

    def create_event_config(self, filter_id, active=True):
        """Create an event configuration.
        
        Args:
            filter_id (str): URN of filter to create an event from.
            active (bool, optonal): If True, event will be active.
        
        Returns:
             str: URN of the created configuration (or None if unsuccessful.)
             
        """
        url = self.url + "/incidentConfigs"
        body = json.dumps({"$savedSearch": filter_id, "active": active})
        logging.info("createIncidentConfig " + str(body))
        response = requests.post(url, verify=True, headers=set_headers(self.api_key), data=body)
        if not response.ok:
            logging.error("createIncidentConfig:" + str(response))
            return None
        the_id = json.loads(response.text)["$id"]
        logging.info("Created incidentConfig with id " + str(the_id))
        return the_id
