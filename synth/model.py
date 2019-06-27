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
import device_factory
from os import path
from common import importer
from directories import *

MODEL_FIELDS_BECOME_PROPERTIES = True

class Model():
    def __init__(self, filepath, instance_name, client, engine, update_callback, context):
        self.instance_name = instance_name
        self.client = client
        self.engine = engine
        self.update_callback = update_callback
        self.context = context

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
                self.models.append(elem)
            else:
                assert "Element of model file "+filepath+" contains neither hierarchy or model: "+str(elem)

    def enact_models(self, models):
        for m in models:
            if "devices" in m:
                properties = self.collect_properties(self.find_matching_models(m))
                for d in m["devices"]:
                    device = self.create_device(d)
                    device.set_properties(properties) 
                    if MODEL_FIELDS_BECOME_PROPERTIES:
                        device.set_properties(m["model"])

    def find_matching_models(self, desired):
        match = [True] * len(self.models)   # A flag for every model entry
        for h in self.hierarchy:
            if h in desired: 
                for i in range(len(self.models)):
                    if h in self.models[i]["model"]:
                        if self.models[i]["model"][h] != desired[h]:
                            match[i] = False
        result = []
        for i in range(len(self.models)):
            if match[i]:
                result.append(self.models[i])

        return result

    def collect_properties(self, models):
        props = {}
        for m in models:
            if "properties" in m:
                props.update(m["properties"])
        return props

    def create_device(self, name):
        params = { "functions" : { name : {} } }   # The structure that device_factory expects 
        device = device_factory.create_device((self.instance_name, self.client, self.engine, self.update_callback, self.context, params))
        return device

# model = importer.get_class('model', name)

def use_model_file(args):
    (instance_name, client, engine, update_callback, context, params) = args
    filename = params["file"]
    model = Model(SCENARIO_DIR + filename, instance_name, client, engine, update_callback, context)

