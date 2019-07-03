"""
variable
========
Creates device properties which can be static (if "value" is defined)
or driven by some timefunction (if "timefunction" is defined)

Configurable parameters::

    {
        "name" : the name of the variable
        "value" : a static number or string - or an array to pick one randomly OR
        "timefunction" : a timefunction definition OR
        "random_lower", "random_upper" : a range of values to pick randomly within (with optional "precision" parameter) OR
        "randstruct" : "["A definition like this where",[" lists "," are "," concatenated"], " and tuples are ("chosen from","selected betwixt"), "randomly]" OR
        "series" : a list: first device gets first value, second device second value etc.
    }

    -or-

    [an array of the above to create multiple properties]

Device properties created::

    {
        <name> : (properties are created according to the "name" argument)
    }
    
"""
   
import logging
import random
from device import Device
from common import importer
from helpers import randstruct

class Variable(Device):
    device_count = -1
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """A property whose value is static or driven by some time function."""
        def create_var(params):
            var_name = params["name"]
            if "value" in params:
                var_value = params["value"]
                if type(var_value) == list:
                    var_value = random.choice(var_value)
                self.set_property(var_name, var_value)
            elif "timefunction" in params:
                tf_name = params["timefunction"].keys()[0]
                var_value = importer.get_class("timefunction", tf_name)(engine, self, params["timefunction"][tf_name])
                self.set_property(var_name, var_value.state())
                engine.register_event_at(var_value.next_change(), self.tick_variable, (var_name, var_value), self)
            elif "random_lower" in params:
                lower = float(params["random_lower"])
                upper = float(params["random_upper"])
                precision = params.get("precision", 1)
                var_value = lower + random.random() * (upper-lower)
                var_value = int(var_value * precision) / float(precision)
                self.set_property(var_name, var_value)
            elif "randstruct" in params:
                var_value = randstruct.evaluate(params["randstruct"])
                self.set_property(var_name, var_value)
            elif "series" in params:
                series = params["series"]
                var_value = series[Variable.device_count % len(series)]
                self.set_property(var_name, var_value)
            else:
                assert False,"variable " + var_name + " must have either value, timefunction, random_lower/upper, randstruct or series"
            self.variables.append( (var_name, var_value) )

        super(Variable, self).__init__(instance_name, time, engine, update_callback, context, params)
        Variable.device_count += 1
        self.variables = [] # List of (name, value) and <value> may be a static value or a timefunction 
        if type(params["variable"]) == dict:
            create_var(params["variable"])
        else:
            for v in params["variable"]:
                create_var(v)

    def comms_ok(self):
        return super(Variable, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Variable, self).external_event(event_name, arg)

    def close(self):
        super(Variable, self).close()

    # Private methods

    def tick_variable(self, args):
        (name, function) = args
        new_value = function.state()
        self.set_property(name, new_value)
        self.engine.register_event_at(function.next_change(), self.tick_variable, args, self)
