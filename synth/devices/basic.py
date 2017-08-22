from device import Device
"""A basic device implementation"""
import random
import logging

class Basic(Device):
    device_number = 0
    def __init__(self, time, engine, update_callback, params):
        self.engine = engine
        self.update_callback = update_callback
        self.properties = {}
        self.properties["$id"] = "-".join([format(random.randrange(0,255),'02x') for i in range(6)])  # A 6-byte MAC address 01-23-45-67-89-ab
        self.properties["is_demo_device"] = True
        self.properties["label"] = "Thing "+str(Basic.device_number)
        self.do_comms(self.properties) # Communicate ALL properties on boot
        Basic.device_number = Basic.device_number + 1
        
    def external_event(self, event_name, arg):
        logging.info("Received external event "+event_name+" for device "+str(self.properties["$id"]))

    def comms_ok(self):
        return True

    def tick_product_usage(self, _):
        if self.propertyAbsent("battery") or self.getProperty("battery") > 0:
            self.setProperty("buttonPress", 1)
            t = timewave.next_usage_time(self.engine.get_now(), ["Mon","Tue","Wed","Thu","Fri"], "06:00-09:00")
            self.engine.register_event_at(t, self.tick_product_usage, self)
        
    def do_comms(self, properties):
        t = self.engine.get_now()
        if self.comms_ok():
            if self.update_callback:
                if not "$ts" in properties: # Ensure there's a timestamp
                    properties["$ts"] = t
                self.update_callback(self.properties["$id"], t, properties)
            else:
                logging.warning("No callback installed to update device properties")

    def get_property(self, prop_name):
        return self.properties[prop_name]

    def property_exists(self, prop_name):
        return prop_name in self.properties

    def property_absent(self, prop_name):
        return not self.property_exists(prop_name)
    
    def set_property(self, prop_name, value):
        """Set device property and transmit an update"""
        new_props = { prop_name : value, "$id" : self.properties["$id"], "$ts" : self.engine.get_now() }
        self.properties.update(new_props)
        self.do_comms(new_props)

    def set_properties(self, new_props):
        new_props.update({ "$id" : self.properties["$id"], "$ts" : self.engine.get_now() })  # Force ID and timestamp to be correct
        self.properties.update(new_props)
        self.do_comms(new_props)

