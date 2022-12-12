"""
basic
=====
This function is inherited by all devices automatically. It does not need to be explicitly declared, unless you want to change its behaviour

Configurable parameters::

    {
        "label_root" : (optional) the root name of the label property
        "use_label_as_$id" : (optional) - if true then instead of creating a "label" property, the $id property is given the label name  (i.e. human-named $id)
        "always_send_metadata" : ["list", "of", "metadata"] - if defined, then all transmissions will be enriched with these metadata properties
        "no_metadata" : If true then doesn't send metadata
        "labels" : A list of values to use as labels
    }

Device properties created::

    {
        "$id" : a unique random property which looks like a MAC address
        "is_demo_device" : to identify that this is a Synth-created device
        "label" : A human-readable label "Device 0", "Device 1" etc.
    }
"""

import random
import logging
import isodate
from .device import Device
from common import importer

class Basic(Device):
    device_number = 0
    myRandom = random.Random()  # Use our own private random-number generator, so we will repeatably generate the same device ID's regardless of who else is asking for random numbers
    myRandom.seed(1234)
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        self.instance_name = instance_name
        self.creation_time = time
        self.engine = engine
        self.update_callback = update_callback
        if not hasattr(self, "properties"):
            self.properties = {}
        self.model = None   # May get set later if we're in a model
        label_root = "Device "
        use_label_as_id = False
        self.always_send_metadata = None
        self.no_metadata = False
        self.clock_skew = 0 # Clock skew is the amount ADDED to our timestamp when we send, i.e. a positive clock skew means that our clock is fast
        if "basic" in params:   # Will only be there if the basic class has been explictly declared (because user wants to override its behaviour)
            label_root = params["basic"].get("label_root", "Device ")
            use_label_as_id = params["basic"].get("use_label_as_$id", False)
            if "clock_skew_max_advance" in params["basic"]:
                max_advance = isodate.parse_duration(params["basic"].get("clock_skew_max_advance")).total_seconds()
                max_retard = isodate.parse_duration(params["basic"].get("clock_skew_max_retard")).total_seconds() 
                skew = Basic.myRandom.random() * (max_advance - max_retard)
                self.clock_skew = max_retard + skew
            self.always_send_metadata = params["basic"].get("always_send_metadata", None)
            self.no_metadata = params["basic"].get("no_metadata", False)

        if not self.no_metadata:
            self.properties["is_demo_device"] = True    # Flag this device so it's easy to delete (only) demo devices from an account that has also started to have real customer devices in it too.

        if "labels" in params.get("basic",{}):
            labs = params["basic"]["labels"]
            label = labs[Basic.device_number % len(labs)]
        else:
            label = label_root + str(Basic.device_number)

        if use_label_as_id:
            self.properties["$id"] = label  # label.replace(" ","_") # Should really replace ALL illegal characters
        else:
            if not "$id" in self.properties:
                self.properties["$id"] = "-".join([format(Basic.myRandom.randrange(0,255),'02x') for i in range(6)])  # A 6-byte MAC address 01-23-45-67-89-ab
            if not self.no_metadata:
                self.properties["label"] = label

        if not self.no_metadata:    # What no_metadata really means is "don't spew stuff out at boot"
            self.do_comms(self.properties, force_comms=True) # Communicate ALL properties on boot (else device and its properties might not be created if comms is down).
        logging.info("Created device " + str(Basic.device_number+1) + " : " + self.properties["$id"])
        Basic.device_number = Basic.device_number + 1
        self.in_property_group = False
        
    def external_event(self, event_name, arg):
        logging.info("Received external event "+event_name+" for device "+str(self.properties["$id"]))

    def close(self):
        pass

    def comms_ok(self):
        return True

    def set_id(self, new_id):
        """Set device id - call this before super() in child classes if you want to override the id that this base class will normally set """
        if not hasattr(self, "properties"):
            self.properties = {}
        self.properties.update({ "$id" : new_id })

    def enrich_metadata(self, properties):
        for p in self.always_send_metadata:
            if p not in properties:
                if p in self.properties:
                    properties[p] = self.properties[p]
        return properties

    def _transmit(self, the_id, ts, properties):
        if self.always_send_metadata is not None:
            properties = self.enrich_metadata(properties)

        if self.update_callback:
            self.update_callback(the_id, ts, properties)
        else:
            logging.warning("No callback installed to update device properties")

    def transmit(self, the_id, ts, properties, force_comms):
        if not self.comms_ok() and not force_comms:
            return
        # logging.info("Doing transmit")
        self._transmit(the_id, ts, properties)
    
    # Internal methods

    def do_comms(self, properties, force_comms = False, timestamp = None):
        if timestamp == None:
            timestamp = self.engine.get_now() + self.clock_skew
        if not "$id" in properties: # Ensure there's an ID
            properties["$id"] = self.properties["$id"]
        if not "$ts" in properties: # Ensure there's a timestamp
            properties["$ts"] = timestamp
        # logging.info("About to self.transmit")
        self.transmit(self.properties["$id"], timestamp, properties, force_comms)

    def get_property(self, prop_name, default_value=None):
        if default_value is not None:
            if self.property_absent(prop_name):
                return default_value
        return self.properties[prop_name]

    def get_property_or_None(self, prop_name):
        if self.property_absent(prop_name):
            return None
        return self.properties[prop_name]

    def property_exists(self, prop_name):
        return prop_name in self.properties

    def property_absent(self, prop_name):
        return not self.property_exists(prop_name)
    
    def get_properties(self):
        return self.properties

    def set_property(self, prop_name, value,
                     always_send = True,
                     force_send = False,
                     timestamp = None):
        """Set device property and transmit an update"""
        if not prop_name in self.properties:
            changed = True
        elif self.properties[prop_name] != value:
            changed = True
        else:
            changed = False

        if timestamp == None:
            timestamp = self.engine.get_now() + self.clock_skew

        new_props = { prop_name : value, "$id" : self.properties["$id"], "$ts" : timestamp }
        self.properties.update(new_props)
        # logging.info("set_prop")
        if changed or always_send:
            # logging.info("c or as")
            if self.in_property_group:
                # logging.info("in group")
                self.property_group.update(new_props)
            else:
                # logging.info("not in group")
                self.do_comms(new_props, timestamp = timestamp, force_comms = force_send)

    def set_properties(self, new_props):
        np = new_props.copy()
        np.update({ "$id" : self.properties["$id"], "$ts" : self.engine.get_now() + self.clock_skew })  # Force ID and timestamp to be correct
        self.properties.update(np)
        self.do_comms(np)    # TODO: Suppress if unchanged

    def start_property_group(self):
        """Mark the beginning of a group of set_property() updates, which we want to group as a single message"""
        assert self.in_property_group == False
        self.in_property_group = True
        self.property_group = {}

    def end_property_group(self):
        assert self.in_property_group == True
        self.do_comms(self.property_group)

        self.in_property_group = False
        self.property_group = {}
