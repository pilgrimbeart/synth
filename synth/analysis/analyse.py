"""
Analyses value streams to detect anomalies
"""
#
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

import glob
import json
import json_inc
import logging
from numbers import Number

class Property_stream():
    """ Analyses a stream of values for anomalies """
    def __init__(self):
        self.min_value = None
        self.max_value = None

    def update(self, value, context):
        surprise = 0

        if self.min_value is None:
            self.min_value = value 
            self.max_value = value
        else:
            if self.min_value == self.max_value:
                if value != self.min_value:
                    self.min_value = min(self.min_value, value)
                    self.max_value = max(self.max_value, value)
                    surprise = 1

            else:
                if value < self.min_value:  # Exceeded lower bound
                    if context[1].startswith("0f-64-e2"):
                        logging.info("Exceeded lower bound")
                    if not isinstance(value, Number):
                        surprise = 1    # It's different, but we can't say by how much
                    else:
                        surprise = float(self.min_value - value) / (self.max_value - self.min_value) # 100% further that past range => 1.0 surprise
                    self.min_value = value
                elif value > self.max_value: # Exceeded upper bound
                    if context[1].startswith("0f-64-e2"):
                        logging.info("Exceeded upper bound")
                    if not isinstance(value, Number):
                        surprise = 1
                    else:
                        surprise = float(value - self.max_value) / (self.max_value - self.min_value) # 100% further that past range => 1.0 surprise
                    self.max_value = value

            if context[1].startswith("0f-64-e2"):
                logging.info(str(context) + ":" + str(value) + " surprise = " + str(surprise) )
        surprise = min(1.0, surprise)
        return surprise

class Device():
    """ An object to hold the state of each device """
    def __init__(self, device_id):
        self.prop_state = {}   # Last-known state of each property
        self.prop_time = {}    # Last-known timestamp of each property
        self.device_id = device_id 
        self.prop_stream = {}   # one for each property
        self.time_stream = {}   # Ditto for timestamps

    def update_property(self, prop, value, timestamp, context):
        # logging.info("update_property(prop="+str(prop)+", value="+str(value)+")")
        if prop not in self.prop_state: 
            prev_state = None
            prev_time = None
            self.prop_stream[prop] = Property_stream()
            self.time_stream[prop] = Property_stream()
            result_state = 1.0  # Creation of a new property => complete surprise
            result_time = 1.0
        else:
            prev_state = self.prop_state[prop]  # TOO: We don't use previous state yet
            prev_time = self.prop_time[prop]
            result_state = self.prop_stream[prop].update(value, context + [prop])
            result_time = self.time_stream[prop].update(timestamp - prev_time, context + ["ts"] + [prop])

        self.prop_state[prop] = value
        self.prop_time[prop] = timestamp

        return [result_state, result_time]

class Analyser():
    """ Analyses a stream of messages """
    def __init__(self):
        self.last_timestamp_processed = None 
        self.devices = {}   # Last-known state of all devices

    def process(self, message):
        if self.last_timestamp_processed is not None:
            assert self.last_timestamp_processed <= message["$ts"], "Records not in time sequence"

        # Ensure we know about this device
        d = message["$id"]
        if d not in self.devices:
            self.devices[d] = Device(d)
        device = self.devices[d]

        t = message["$ts"]
        results = []
        for prop, val in message.iteritems():
            if prop not in ["$id", "$ts"]:
                results += device.update_property(prop, val, t, context=[t,d]) 

        surprise = float(sum(results))/len(results)

        struc = { "$id" : d, "$ts" : t, "ML_anomaly" : surprise }
        return struc

class Analyse_files():
    def __init__(self, input_filespec, output_filestem):
        self.last_timestamp_processed = None 
        self.devices = {}   # Last-known state of all devices
        self.input_filespec = input_filespec
        self.analyser = Analyser()
        self.writer = json_inc.Writer(output_filestem)

    def __del__(self):
        self.writer.close()

    def analyse(self):
        num_records = 0
        for f in glob.glob(self.input_filespec):
            logging.info("Ingesting " + f)
            data = json.loads(open(f, "rt").read())
            logging.info("[" + str(len(data)) + " records]")
            num_records += len(data)
            for r in data:
                result = self.analyser.process(r)
                self.writer.write(result)
        logging.info("[" + str(num_records) + " total records]")
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Here we go...")
    a = Analyse_files("../../../synth_logs/OnFStest0*.json", "analyse")
    a.analyse()

