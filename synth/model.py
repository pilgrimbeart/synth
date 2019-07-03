"""MODEL
   Reasons on a model of the world."""
#
# Copyright (c) 2019 DevicePilot Ltd.
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

import logging
import json
import copy
import device_factory
from os import path
from common import importer
from directories import *

MODEL_FIELDS_BECOME_PROPERTIES = True

def enumerate_model_counter(struc):
    # Given a dict this checks whether any of its values is a special counting value, and if so 'enumerates' it, generating a dict for all values in the specified range

    # Is there a counting value?
    the_key = None
    for k in struc["model"].keys():
        if struc["model"][k].find("#") != -1:
            the_key = k
            break
    if the_key is None:
        return [ struc ]

    # Decode it (correct format is "*#N#*" where * is anything or nothing)
    parts = struc["model"][the_key].split("#")
    N = int(parts[1])

    # Explode it
    L = []
    for i in range(N):
        s = copy.deepcopy(struc)
        s["model"][the_key] = parts[0] + str(i) + parts[2]
        L.append(s)
    return L

class Model():
    def __init__(self, filepath, instance_name, client, engine, update_callback, context):
        self.instance_name = instance_name
        self.client = client
        self.engine = engine
        self.update_callback = update_callback
        self.context = context
        self.devices = []

        self.load_file(filepath)
        self.enact_models(self.models)

    def load_file(self, filepath):
        logging.info("Loading model file "+str(filepath))
        struc = json.loads(open(filepath, "rt").read())    # We expect a list of dicts
        self.hierarchy = None
        self.models = []
        for elem in struc:
            if "hierarchy" in elem:
                self.hierarchy = elem["hierarchy"].split("/")
            elif "model" in elem:
                for e in enumerate_model_counter(elem):
                    self.models.append(e)
            else:
                assert "Element of model file "+filepath+" contains neither hierarchy or model: "+str(elem)

    def enact_models(self, models):
        for m in models:
            if "devices" in m:
                properties = self.collect_properties(self.find_matching_models(m))
                number = m.get("count", 1)
                for device_spec in m["devices"]:
                    for count in range(number):
                        device = self.create_device(device_spec)
                        device.model = self
                        device.model_spec = m
                        device.set_properties(properties) 
                        if MODEL_FIELDS_BECOME_PROPERTIES:
                            device.set_properties(m["model"])

    def collect_properties(self, models):
        props = {}
        for m in models:
            if "properties" in m:
                props.update(m["properties"])
        return props

    def create_device(self, device_spec):
        params = { "functions" : device_spec }   # The structure that device_factory expects 
        device = device_factory.create_device((self.instance_name, self.client, self.engine, self.update_callback, self.context, params))
        self.devices.append(device)
        return device

    def find_matching_models(self, desired):
        # TODO: If models get large, this needs to be rewritten to use set intersection
        match = [True] * len(self.models)   # A flag for every model entry
        for h in self.hierarchy:
            if h in desired["model"]: 
                for i in range(len(self.models)):
                    if h in self.models[i]["model"]:
                        if self.models[i]["model"][h] != desired["model"][h]:
                            match[i] = False
        result = []
        for i in range(len(self.models)):
            if match[i]:
                result.append(self.models[i])
        return result

    def get_peers(self, device):
        # Get all other devices which are at the same level of the model
        peers = []
        for d in self.devices:
            if d != device:
                if d.model_spec == device.model_spec:
                    peers.append(d)
        return peers

    def get_peers_and_below(self, device):
        # logging.info("get_peers_and_below for "+str(device.get_property("$id")))
        desired = device.model_spec
        # logging.info("desired = "+str(desired))
        devs = []
        for d in self.devices:
            if d != device:
                # logging.info("Checking "+str(d.model_spec))
                match = True
                for h in self.hierarchy:
                    if h in desired["model"]:
                        if h in d.model_spec["model"]:
                            if desired["model"][h] != d.model_spec["model"][h]:
                                match = False
                if match:
                    devs.append(d)
                    # logging.info("Match: "+str(d.model_spec))
        return devs


# model = importer.get_class('model', name)

def use_model_file(args):
    (instance_name, client, engine, update_callback, context, params) = args
    filename = params["file"]
    model = Model(SCENARIO_DIR + filename, instance_name, client, engine, update_callback, context)

