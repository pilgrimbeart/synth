"""
Analyses value streams to detect anomalies.
This is intentionally as simple an analyser as possible to occupy a place in the framework which could later be replaced by something arbitrarily-complex (Bayesian, ML etc.)

Class hierarchy:
    Analyse_files                   Can ingest files
        Analyser                    Analyses messages one at a time, creating new devices as necessary
            Device                  Splits messages into value-streams and timestamp-streams, each of which is a...
                Property_stream     Which calculates a "surprise" value for each new value fed to it

There are two types of Property_stream:
    . Continuous                    Integers and Floats, which can be binned and histogrammed
    . Discrete                      Strings and Bools, which can be histogrammed directly [in principle we should use this for enumerated types too]
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

HISTO_BINS = 10
HISTORY_LENGTH = 1000

def is_value_continuous(value, context):
    if type(value) in [int, float]:
        return True
    elif type(value) in [bool, str, unicode]:
        return False
    elif value==None:
        logging.warning("None type supplied as first value of a property - assuming it's discrete "+str(context))
        return False
    else:
        assert False,"Cannot infer type from " + str(type(value))


class Property_stream_continuous():
    """ Analyses a stream of values for anomalies """
    def __init__(self):
        self.min_value = None   # i.e. bottom edge of bin[0]
        self.max_value = None   # i.e. top edge of bin[HISTO_BINS-1]
        self.histogram = []     # A histogram of HISTO_BINS, i.e. a count of how many values have been seen in each portion of the range min_value..max_value
        self.history = []       # Last HISTORY_LENGTH values seen (only used to recalculate the histogram]. 

    def update(self, value, context):
        if type(value) == unicode:
            assert False, "String value passed to continuous update: " + repr(context) + " : " + repr(value)

        #if context[1].startswith("f6-70-01"):
        #   logging.info(str(context) + ":" + str(value))

        if(len(self.history) >= HISTORY_LENGTH):
            self.history = self.history[1:]
        self.history.append(value)
        # logging.info("history = "+str(self.history))

        if (self.min_value is None):                # Never seen anything before, so anything is surprising
            self.calculate_histogram()
            surprise = 1.0
        elif (self.min_value == self.max_value):    # We've only ever seen one value before, so if it's the same then unsurprising, otherwise totally surprising
            self.calculate_histogram()
            if value == self.min_value:
                surprise = 0.0
            else:
                surprise = 1.0                      # we don't yet have any scale to judge HOW surprising
        else:
            if (value < self.min_value):
                surprise = min(1.0, float(self.min_value - value) / (self.max_value - self.min_value)) # 100% further that past range => 1.0 surprise
                self.calculate_histogram()
            elif (value > self.max_value):
                surprise = min(1.0, float(value - self.max_value) / (self.max_value - self.min_value)) # 100% further that past range => 1.0 surprise
                self.calculate_histogram()
            else:   # Within range of existing histogram
                binsize = float(self.max_value - self.min_value) / HISTO_BINS
                bin = int(min(HISTO_BINS-1, (value - self.min_value) / binsize))
                # logging.info("bin="+str(bin))
                surprise = 1.0 - float(self.histogram[bin]) / sum(self.histogram)
                if False and context[1].startswith("04-81-01") and context[2]=="temperature":
                    logging.info("Within range. binsize="+str(binsize)+" bin="+str(bin) + " thisBinCount="+str(self.histogram[bin]) + " histo sum is "+str(sum(self.histogram)))
                self.histogram[bin] += 1

            # if context[1].startswith("f6-70-01"):
            #    logging.info(str(context) + ":" + str(value) + " surprise = " + str(surprise) )

        if False and "Vehicle_321" in context and context[2]=="tire_pressure_psi":
            logging.info(str(context)+" continuous value="+str(value)+" surprise="+str(surprise) + "       ->   "+str(self.histogram)+ " " + str(len(self.history))+ " " + str((self.min_value, self.max_value)))

        #if context[1].startswith("04-81-01") and context[2]=="temperature":
        #logging.info(str(context) + ":" + str(value) + " surprise="+str(surprise))
        #logging.info("min,max=" + str((self.min_value, self.max_value)) + " histogram="+str(self.histogram))
        #logging.info("")

        return surprise

    def calculate_histogram(self):
        # logging.info("Calculating histogram of history "+str(self.history))
        self.histogram = [0] * HISTO_BINS
        self.min_value = min(self.history)
        self.max_value = max(self.history)
        binsize = float(self.max_value - self.min_value) / HISTO_BINS
        # logging.info("min="+str(self.min_value)+" max="+str(self.max_value) + " binsize="+str(binsize))
        if binsize == 0:
            return
        for v in self.history:
            bin = min(int((v - self.min_value) / binsize), HISTO_BINS-1)
            # logging.info("bin="+str(bin)+" v="+str(v))
            self.histogram[bin] += 1
        # logging.info("Histogram is: "+str(self.histogram))


class Property_stream_discrete():
    """ Analyses a stream of values for anomalies """
    def __init__(self):
        self.histogram = {}
        self.unique_count = 0

    def histo_sum(self):
        sum = 0
        for k,v in self.histogram.iteritems():
            sum += v
        return sum

    def update(self, value, context):
        if value in self.histogram:
            surprise = 1.0 - float(self.histogram[value]) / self.histo_sum()
            # logging.info("Existing value. "+str(self.histogram[value]))
        else:
            self.histogram[value] = 0
            self.unique_count += 1
            surprise = 1.0
        self.histogram[value] += 1

        #if "Vehicle_321" in context:
        #    logging.info("discrete value="+str(value)+" surprise="+str(surprise))
        return surprise


class Device():
    """ An object to hold the state of each device """
    def __init__(self, device_id):
        self.prop_state = {}   # Last-known state of each property
        self.prop_time = {}    # Last-known timestamp of each property
        self.device_id = device_id 
        self.prop_stream = {}   # a Property Stream for each property
        self.time_stream = {}   # Ditto for timestamps

    def update_property(self, prop, value, timestamp, is_continuous, context):
        # logging.info("update_property(prop="+str(prop)+", value="+str(value)+")")
        if prop not in self.prop_state: 
            # logging.info("Create new property "+repr(prop)+"="+repr(value)+" where is_continuous= "+repr(is_continuous))
            prev_state = None
            prev_time = None
            if is_continuous:
                self.prop_stream[prop] = Property_stream_continuous()
            else:
                self.prop_stream[prop] = Property_stream_discrete()
            self.time_stream[prop] = Property_stream_continuous()
            result_state = 1.0  # Creation of a new property => complete surprise
            result_time = 1.0
        else:
            prev_state = self.prop_state[prop]  # TOO: We don't use previous state yet
            prev_time = self.prop_time[prop]
            result_state = self.prop_stream[prop].update(value, context + [prop])
            result_time = self.time_stream[prop].update(timestamp - prev_time, context + ["ts"] + [prop])

        self.prop_state[prop] = value
        self.prop_time[prop] = timestamp

        return (result_state, result_time)

class Analyser():
    """ Analyses a stream of messages """
    def __init__(self):
        self.last_timestamp_processed = None 
        self.devices = {}   # Last-known state of all devices
        self.prop_is_continuous = {} # For each property, whether it's continuous or discrete (we maintain this here, rather than in individual property streams, because we might get a property set to e.g. a string on one device, then to None as the first value on another device (and you can't infer type from None)

    def process(self, message):
        if self.last_timestamp_processed is not None:
            assert self.last_timestamp_processed <= message["$ts"], "Records not in time sequence"

        # logging.info(str(message))

        # Ensure we know about this device
        d = message["$id"]
        if d not in self.devices:
            self.devices[d] = Device(d)
        device = self.devices[d]

        t = message["$ts"]
        state_results = []  # A list of (value, property_name) pairs, so we can sort by largest value
        time_results = []
        for prop, val in message.iteritems():
            if prop not in ["$id", "$ts"]:
                if not prop.startswith("ML_"):  # If we're post-processing data that's already had this analysis, don't do analysis on the analysis!
                    if not prop in self.prop_is_continuous:
                        # logging.info("Analyse: New property "+str(prop)+" first found on device "+str(message["$id"]))
                        self.prop_is_continuous[prop] = is_value_continuous(val, message)
                    # logging.info(repr(prop) + " : " + repr(val))
                    (state_result, time_result) = device.update_property(prop, val, t, self.prop_is_continuous[prop], context=[t,d]) 
                    state_results.append((state_result, prop))
                    time_results.append((time_result, prop))
        state_results.sort()
        time_results.sort()

        struc = { "$id" : d, "$ts" : t,
                "ML_anomaly" : state_results[0][0],     "ML_anomaly_property" : state_results[0][1],
                "ML_ts_anomaly" : time_results[0][0],   "ML_ts_anomaly_property" : time_results[0][1],
                }
        # logging.info("struc="+str(struc))
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
    if True:   # Some test files
        a = Analyse_files("../../../synth_logs/OnFStest0*.json", "analyse")
        a.analyse()
    else:
        if True:
            logging.info("TESTING SMOOTH RAMP")
            p = Property_stream_continuous()
            for vv in range(HISTORY_LENGTH * 3):
                v = (HISTORY_LENGTH - vv) / 100.0
                logging.info("For value "+str(v)+" surprise is "+str(p.update(v,["",""]))+"\n")
                raw_input()

        if False:
            logging.info("TESTING NUMBERS")
            p = Property_stream_continuous()
            L = [0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,0,0,-1,20,100,-100]
            for v in L:
                logging.info("For value "+str(v)+" surprise is "+str(p.update(v,["",""]))+"\n")
                raw_input()

        if False:
            logging.info("TESTING STRINGS")
            p = Property_stream_discrete()
            L = ["Fred", "Jim", "Fred", "Fred", "Fred", "Fred", "Jim", "Jim", "Mary"]
            for v in L:
                logging.info("For value "+str(v)+" surprise is "+str(p.update(v,["",""]))+"\n")
                raw_input()

