"""
repeater
=====
Emits properties (that are created and managed by other behaviours) metronomically

Configurable parameters::

    {
        "period" : "PT1H" - how often to emit the properties
        "properties" : ["A","list","of","them"]
    }

Device properties created::

    {
        <whatever is in the "properties" list>
    }
"""
import logging
import time
import isodate

from .device import Device

class Repeater(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Repeater,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.repeater_period = isodate.parse_duration(params["repeater"]["period"]).total_seconds()
        self.repeater_properties = params["repeater"]["properties"]
        self.engine.register_event_in(self.repeater_period, self.tick_emit, self, self)

    def comms_ok(self):
        return super(Repeater,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Repeater,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Repeater,self).close()

    # Private methods
    def tick_emit(self, _):
        props = {}
        for p in self.repeater_properties:
            props[p] = self.get_property(p)
        self.set_properties(props)
        self.engine.register_event_in(self.repeater_period, self.tick_emit, self, self)
