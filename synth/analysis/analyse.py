import glob
import json
import logging

class Property_stream():
    """ Analyses a stream of values for anomalies """
    def __init__(self):
        self.min_value = None
        self.max_value = None

    def update(self, value, previous_value, context):
        # logging.info("update "+str(value)+","+str(previous_value))
        surprise = 0

        if self.min_value is None:
            self.min_value = value
        else:
            if value < self.min_value:
                # logging.info(str(context) + " surprise - value exceeded lower bound "+str(self.min_value)+", "+str(value))
                self.min_value = value
                surprise = 1

        if self.max_value is None:
            self.max_value = value
        else:
            if value > self.max_value:
                # logging.info(str(context) + " surprise - value exceeded upper bound "+str(self.max_value)+", "+str(value))
                self.max_value = value
                surprise = 1

        return surprise

class Device():
    """ An object to hold the state of each device """
    def __init__(self, device_id):
        self.state = {}             # Last-known state of each property
        self.device_id = device_id  # Will get sent in properties, but helpful to know it up-front before we even see the first $id property
        self.prop_stream = {}   # one for each property

    def update_property(self, prop, value, timestamp, context):
        # logging.info("update_property(prop="+str(prop)+", value="+str(value)+")")
        if prop not in self.state:
            prev = None
            self.prop_stream[prop] = Property_stream()
        else:
            prev = self.state[prop]

        result = self.prop_stream[prop].update(value, prev, context + [prop])

        self.state[prop] = value

        return result

class Analyser():
    """ Analyses a stream of messages """
    def __init__(self, input_filespec, output_filepath):
        self.last_timestamp_processed = None 
        self.input_filespec = input_filespec
        self.devices = {}   # Last-known state of all devices
        self.output_file = open(output_filepath, "wt")
        self.output_file.write("[\n")
        self.first_write = True

    def __del__(self):
        self.output_file.write("\n]")
        self.output_file.close()

    def analyse(self):
        num_records = 0
        for f in glob.glob(self.input_filespec):
            logging.info("Ingesting " + f)
            data = json.loads(open(f, "rt").read())
            logging.info("[" + str(len(data)) + " records]")
            num_records += len(data)
            for r in data:
                self.process(r)
        logging.info("[" + str(num_records) + " total records]")

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
            results += [ device.update_property(prop, val, t, context=[t,d]) ] 

        surprise = float(sum(results))/len(results)

        struc = { "$id" : d, "$ts" : t, "ML_anomaly" : surprise }
        if self.first_write:
            self.first_write = False
        else:
            self.output_file.write(",\n")
        self.output_file.write(json.dumps(struc, sort_keys=True))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Here we go...")
    a = Analyser("../../../synth_logs/OnFStest0*.json", "surprise.json")
    a.analyse()

