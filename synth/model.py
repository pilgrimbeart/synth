"""MODEL
=====
   Build a model of the world, top-down
   
  A model file is a JSON list of declarations. There are two types of declaration:

      "hierarchy" : "company/town/floor/zone" 
      "model" : { "company" : "Harrods", "town" : "London", "floor" : 0, "zone" : "Admin" }
   
    Each model declaration matches one or more of the levels of the hierarchy (and any levels that it doesn't
    declare are considered to be wildcards.

    Each model may define:
        "devices" - the same as the "functions" element in a "create_device" action of a normal scenario file
        "properties" - a set of property (name : value) pairs

    The properties get attached to that level of the model, and inherited by all devices
    at that level of the model and below. For example in the above model, you could declare a latitude
    and a longitude property, and those properties would get inherited by any device also at that level
    (in this declaration or any other).
    For example a weather station attached to the Harrods store in London would inherit the lat,lon, and so
    would any devices in that store, e.g. a fridge in the Admin zone of the ground floor of Harrods in London.

    The above helps create a "top down" declarative structure to your Synth simulations.

    Devices can also find out what model hierarchy they exist within. For example the Disruptive Technology
    device behaviour can use the model to discover if it is in the same part of a model as other devices.
    Thus proximity sensors attached to fridge doors can make the fridge get warm if they are left open.


    Helpful shortcuts for rapid modelling:

    . If you name a model element  "fridge" : "Fridge #2#"  then this is equivalent to two model
      declarations for "Fridge 1" and "Fridge 2".

    . If you name a model element  "building" : "['Building ', ('Lavel','Maurice')]" then, in conjuction with the
      numbering scheme above, each fridge will be in either the "Building Lavel" or "Building Maurice" building
      within the model, randomly.

   """
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
from common import randstruct
from directories import *

MODEL_FIELDS_BECOME_PROPERTIES = True

def randomise(s):
# If string s contains a "randomise me" list of choices, then turn it into one of its choices
    if s.startswith("[") and s.endswith("]"):
        s = randstruct.evaluate(s)

def enumerate_model_counter(struc):
    # Given a dict this checks whether any of its values is a special counting value, and if so 'enumerates' it, generating a dict for all values in the specified range

    # Is there a counting value?
    the_key = None
    for k in struc["model"]:
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
        s["model"][the_key] = parts[0] + str(i+1) + parts[2]    # Start counting at 1
        for k in s["model"]:
            randomise(s["model"][k])

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

