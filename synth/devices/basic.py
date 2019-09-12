"""
basic
=====
This function is inherited by all devices automatically. It does not need to be explicitly declared, unless you want to change its behaviour

Configurable parameters::

    {
        "label_root" : (optional) the root name of the label property
        "use_label_as_$id" : (optional) - if true then instead of creating a "label" property, the $id property is given the label name  (i.e. human-named $id)
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
from device import Device
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
        self.properties = {}
        self.properties["is_demo_device"] = True    # Flag this device so it's easy to delete (only) demo devices from an account that has also started to have real customer devices in it too.
        self.model = None   # May get set later if we're in a model
        label_root = "Device "
        use_label_as_id = False
        if "basic" in params:   # Will only be there if the basic class has been explictly declared (because user wants to override its behaviour)
            label_root = params["basic"].get("label_root", "Device ")
            use_label_as_id = params["basic"].get("use_label_as_$id", False)
        label = label_root + str(Basic.device_number)
        if use_label_as_id:
            self.properties["$id"] = label.replace(" ","_") # Should really replace ALL illegal characters
        else:
            self.properties["$id"] = "-".join([format(Basic.myRandom.randrange(0,255),'02x') for i in range(6)])  # A 6-byte MAC address 01-23-45-67-89-ab
            self.properties["label"] = label
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

    def transmit(self, the_id, ts, properties, force_comms):
        if not self.comms_ok() and not force_comms:
            return

        if self.update_callback:
            self.update_callback(the_id, ts, properties)
        else:
            logging.warning("No callback installed to update device properties")
    
    # Internal methods

    def do_comms(self, properties, force_comms = False, timestamp = None):
        if timestamp == None:
            timestamp = self.engine.get_now()
        if not "$id" in properties: # Ensure there's an ID
            properties["$id"] = self.properties["$id"]
        if not "$ts" in properties: # Ensure there's a timestamp
            properties["$ts"] = timestamp
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
                     timestamp = None):
        """Set device property and transmit an update"""
        if not prop_name in self.properties:
            changed = True
        elif self.properties[prop_name] != value:
            changed = True
        else:
            changed = False

        if timestamp == None:
            timestamp = self.engine.get_now()

        new_props = { prop_name : value, "$id" : self.properties["$id"], "$ts" : timestamp }
        self.properties.update(new_props)
        if changed or always_send:
            if self.in_property_group:
                self.property_group.update(new_props)
            else:
                self.do_comms(new_props, timestamp = timestamp)

    def set_properties(self, new_props):
        np = new_props.copy()
        np.update({ "$id" : self.properties["$id"], "$ts" : self.engine.get_now() })  # Force ID and timestamp to be correct
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
