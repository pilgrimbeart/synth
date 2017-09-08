"""Variable
   A property whose value is driven by some time function"""
   
import logging
from device import Device
from common import importer

class Variable(Device):
    def __init__(self, instance_name, time, engine, update_callback, params):
        """A property whose value is driven by some time function"""
        super(Variable, self).__init__(instance_name, time, engine, update_callback, params)
        self.variable_name = params["variable"]["name"]
        tf = params["variable"]["timefunction"]
        self.variable_timefunction = importer.get_class("timefunction", tf.keys()[0])(engine, tf[tf.keys()[0]])
        self.set_property(self.variable_name, self.variable_timefunction.state())
        engine.register_event_at(self.variable_timefunction.next_change(), self.tick_variable, self)

    def comms_ok(self):
        return super(Variable, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Variable, self).external_event(event_name, arg)

    def finish(self):
        super(Variable, self).finish()

    # Private methods

    def tick_variable(self, _):
        new_value = self.variable_timefunction.state()
        self.set_property(self.variable_name, new_value, always_send=False)
        self.engine.register_event_at(self.variable_timefunction.next_change(), self.tick_variable, self)
