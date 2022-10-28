"""MODEL
=====
   Build a model of the world, top-down
   
  A model file is a JSON list of elements. There are two types of element:

      "hierarchy" : "company/town/floor/zone" 
      "model" : { "company" : "Harrods", "town" : "London", "floor" : 0, "zone" : "Admin" }
   
    Each model element matches zero or more of the levels of the hierarchy
        . any levels that it doesn't declare are considered to match 
        . if you declare an empty model:   "model" : {}   then this will apply to everything in the model

    Each model element will also define at least one of:
        "devices" - devices to be instantiated at this level of the model (i.e. the same as the "functions" element in a "create_device" action of a normal scenario file)
        "properties" - a set of property (name : value) pairs, or name : {parameter} pairs (the latter runs functions in model/ to perform 'smart' property creation)

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
      declarations for "Fridge 1" and "Fridge 2". Multiple "#" elements are enumerated nestedly,
      e.g. {"building" : "Building #3#", "fridge" : "Fridge #4#"} enumerates 4 fridges in each of 3 buildings.

    . If you name a model element  "building" : "['Building ', ('Lavel','Maurice')]" then, in conjuction with the
      numbering scheme above, each fridge will be in either the "Building Lavel" or "Building Maurice" building
      within the model, randomly. Tuples are choices, Lists are concatenations.

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
import random
import isodate
from os import path
from common import importer
from common import randstruct
from directories import *

MODEL_FIELDS_BECOME_PROPERTIES = True

def randomise(s):
# If string s contains a "randomise me" list of choices, then turn it into one of its choices
    if not isinstance(s, str):
        return s
    if s.startswith("[") and s.endswith("]"):
        return randstruct.evaluate(s)
    if s.find("..") != -1:
        p = s.split("..")
        n1 = int(p[0])
        n2 = int(p[1])
        s = random.randint(n1,n2)
        return s
    return s

def enumerate_model_counters(struc):
    # Given a dict this checks whether any of its values are special counting values, and if so 'enumerates' them nestedly, generating a dict for all combinations of specified values
    def increment(i):
        counts[the_keys[i]] += 1
        if counts[the_keys[i]] == totals[the_keys[i]]:
            counts[the_keys[i]] = 0
            if i==len(the_keys)-1:
                return True
            return increment(i+1)
        return False

    # Find any counting values
    the_keys = []
    for k in struc["model"]:
        if struc["model"][k].find("#") != -1:
            the_keys.append(k)
    if the_keys == []:
        return [ struc ]


    # Find the totals
    totals = {}
    counts = {}
    front_parts = {}
    back_parts = {}
    for this_key in the_keys:
        # Decode it (correct format is "*#N#*" where * is anything or nothing
        parts = struc["model"][this_key].split("#")
        assert len(parts) == 3, "Incorrect format of enumerated counter (should be e.g. name#10#) : "+struc["model"][this_key]
        front_parts[this_key] = parts[0]
        totals[this_key] = int(parts[1])
        back_parts[this_key] = parts[2]
        counts[this_key] = 0

    # Explode all/ the counters
    L = []
    while True:
        # for c in the_keys:
        #     print c,":",counts[c]," ",
        # print

        s = copy.deepcopy(struc)
        for k in s["model"]:
            if k in the_keys:
                s["model"][k] = front_parts[k] + str(counts[k]+1) + back_parts[k]   # "+1" because we emit counts which start at 1 not 0
            s["model"][k] = randomise(s["model"][k]) 
        if "properties" in s:
            for p in s["properties"]:
                s["properties"][p] = randomise(s["properties"][p])

        L.append(s)

        if increment(0):
            break

    return L

class Model():
    def __init__(self, specification, instance_name, client, engine, update_callback, context):
        self.instance_name = instance_name
        self.client = client
        self.engine = engine
        self.update_callback = update_callback
        self.context = context
        self.devices = []
        self.cache_gpab = {}    # If we anticipate changing the model after loading, we should invalidate this cache then

        self.load_file(specification)
        self.enact_models(self.models, specification, engine)

    def load_file(self, specification):
        self.hierarchy = None
        self.models = []
        self.model_interval = None
        for elem in specification:
            if "hierarchy" in elem:
                self.hierarchy = elem["hierarchy"].split("/")
            elif "model" in elem:
                for e in enumerate_model_counters(elem):
                    self.render_smart_properties(e)
                    self.models.append(e)
                if "interval" in elem:
                    self.model_interval = isodate.parse_duration(elem["interval"]).total_seconds()
                    logging.info("Spacing-out models by time interval "+str(self.model_interval))
            else:
                assert "Element of model file contains neither hierarchy or model: "+repr(elem)

    def enact_models(self, models, specification, engine):
        def create_device(args):
            (device_space, slf, m, properties, model_props) = args
            device = self.create_device(device_spec)
            device.model = self
            device.model_spec = m
            device.set_properties(properties) 
            if MODEL_FIELDS_BECOME_PROPERTIES:
                device.set_properties(m["model"])

        t = engine.get_now()
        for m in models:
            if "devices" in m:
                properties = self.collect_properties(self.find_matching_models(m))
                number = m.get("count", 1)
                assert type(m["devices"]) == list, "This should be a [{'list':{}}, {'of':{}}, {'dicts':{}}]  :  "+str(m["devices"])
                for device_spec in m["devices"]:
                    assert type(device_spec) == dict, "This should be a {dict} : "+str(device_spec)
                    for count in range(number):
                        engine.register_event_at(t, create_device, (device_spec, self, m, properties, m["model"]), None)
                if self.model_interval is not None:
                    t += self.model_interval


    def collect_properties(self, models):
        props = {}
        for m in models:
            if "properties" in m:
                props.update(m["properties"])
        return props

    def render_smart_properties(self, elem):
        new_props = {}
        if "properties" in elem:
            for n,v in elem["properties"].copy().items():
                if type(v) == dict:
                    model = importer.get_class('model', n)
                    model(self.context, v, new_props)
                    del elem["properties"][n]   # Delete smart property
            elem["properties"].update(new_props)

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
        # Should perhaps be called "get_peers_and_above"!
        # Finds other devices whose model hiearchy matches this device's, insofar as the others define the hierarchy
        # In other words, if other devices only specify one of the hierarchy levels, but in that they match this device, then return the device
        # So for example if a weather device defines "site=X" and you call this function from a device which also defines "site=X" (whatever other model hierarchy levels it defines), it will match
        if device in self.cache_gpab:
            return self.cache_gpab[device]
        desired = device.model_spec
        devs = []
        for d in self.devices:
            if d != device:
                match = True
                for h in self.hierarchy:
                    if h in desired["model"]:
                        if h in d.model_spec["model"]:
                            if desired["model"][h] != d.model_spec["model"][h]:
                                match = False
                if match:
                    devs.append(d)
        self.cache_gpab[device] = devs
        return devs


def use_model(args):
    (instance_name, client, engine, update_callback, context, params) = args
    if "file" in params:
        filepath = SCENARIO_DIR + params["file"]
        logging.info("Loading model file "+str(filepath))
        struc = json.loads(open(filepath, "rt").read())    # We expect a list of dicts
    else:
        struc = params
    model = Model(struc, instance_name, client, engine, update_callback, context)

if __name__ == "__main__":
    def test(length, x):
        print(str(x) + " --> ")
        L = enumerate_model_counters(x)
        for e in L:
            print(" " * (len(str(x)) + 5) + str(e))
        assert len(L) == length

    test( 1, { "model" : { "a" : "A #1#" } } )
    test( 2, { "model" : { "a" : "A #2#" } } )
    test( 1, { "model" : { "a" : "A #1#", "b" : "B #1#" } } )
    test( 2, { "model" : { "a" : "A #1#", "b" : "B #2#" } } )
    test( 2, { "model" : { "a" : "A #2#", "b" : "B #1#" } } )
    test( 4, { "model" : { "a" : "A #2#", "b" : "B #2#" } } )
    test( 27, { "model" : { "a" : "A #3#", "b" : "B #3#", "c" : "C #3#" } } )
    print("Tests passed")

