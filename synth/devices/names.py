"""
names
=====
Provides first name and last name of device owner, chosen randomly hashed by $id.

Configurable parameters::

    {
    }

Device properties created::

    {
        "first_name" : the owner's first name
        "last_name" : the owner's last name
    }
    
"""

from device import Device
from helpers import people_names

class Names(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Names,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.set_properties(
            { 'first_name' : people_names.first_name(self.properties["$id"]),
              'last_name' :  people_names.last_name(self.properties["$id"]) } )

    def comms_ok(self):
        return super(Names,self).comms_ok()
    
    def external_event(self, event_name, arg):
        super(Names,self).external_event(event_name, arg)

    def close(self, err_str):
        super(Names,self).close(err_str)

