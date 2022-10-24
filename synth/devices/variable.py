"""
variable
========
Creates device properties which can be static (if "value" is defined)
or driven by some timefunction (if "timefunction" is defined)

Configurable parameters::

    {
        "name" : the name of the variable
        ONE OF:
            "value" : a static number or string - or an array to pick one randomly
            "timefunction" : a timefunction definition
            "random_lower", "random_upper" : a range of values to pick randomly within (with optional "precision" parameter)
            "randstruct" : "["A definition like this where",[" lists "," are "," concatenated"], " and tuples are ("chosen from","selected betwixt"), "randomly]"
            "series" : a list: first device gets first value, second device second value etc.
            "index" : ratio. The device number * ratio (if ratio==1, first device is 1, second gets 2, etc.)

        (optionally)
        "randomness_property": Name of a property whose value to use for randomness (e.g. location)
        "pick_sequentially" : true to pick values from a list in sequence, not randomly
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
from .device import Device
from common import importer
from common import randstruct

class Variable(Device):
    device_indices = {}  # For every series-type variable we see, this maintains an index into the series
    dev_count = 0
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """A property whose value is static or driven by some time function."""
        def create_var(params):
            self.my_random = random.Random() # We use our own random-number generator, one per variable per device
            rp = params.get("randomness_property", None)
            if rp is None:
                self.my_random.seed(self.get_property("$id"))   # Seed each device uniquely
            else:
                self.my_random.seed(hash(self.get_property(rp)))

            var_name = params["name"]

            pick_seq = params.get("pick_sequentially", False)

            if "value" in params:
                var_value = params["value"]
                if type(var_value) == list:
                    if pick_seq:
                        var_value = var_value[Variable.dev_count % len(var_value)] 
                        Variable.dev_count += 1
                    else:
                        var_value = self.my_random.choice(var_value)
                variables[var_name] = var_value
            elif "timefunction" in params:
                tf_name = list(params["timefunction"].keys())[0]    # We know there's only 1
                var_value = importer.get_class("timefunction", tf_name)(engine, self, params["timefunction"][tf_name])
                variables[var_name] = var_value.state()
                next_change = var_value.next_change()
                engine.register_event_at(next_change, self.tick_variable, (var_name, var_value), self)
            elif "random_lower" in params:
                lower = float(params["random_lower"])
                upper = float(params["random_upper"])
                precision = params.get("precision", 1)
                var_value = lower + self.my_random.random() * (upper-lower)
                var_value = int(var_value * precision) / float(precision)
                variables[var_name] = var_value
            elif "randstruct" in params:
                var_value = randstruct.evaluate(params["randstruct"], self.my_random)
                variables[var_name] = var_value
            elif "series" in params:
                series = params["series"]
                if var_name not in Variable.device_indices:
                    Variable.device_indices[var_name] = 0
                idx = Variable.device_indices[var_name]
                var_value = series[idx % len(series)]
                variables[var_name] = var_value
            elif "index" in params:
                variables[var_name] = int(Variable.dev_count * params["index"])
                Variable.dev_count += 1
            else:
                assert False,"variable " + var_name + " must have either value, timefunction, random_lower/upper, randstruct, series or index"

        super(Variable, self).__init__(instance_name, time, engine, update_callback, context, params)
        variables = {} # Keep all variables in the same message, so store them then update them all 

        if type(params["variable"]) == dict:
            create_var(params["variable"])
        else:
            for v in params["variable"]:
                create_var(v)

        for k in Variable.device_indices:
            Variable.device_indices[k] += 1 

        self.set_properties(variables)

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
        self.set_property(name, new_value, always_send = True)
        next_change = function.next_change()
        self.engine.register_event_at(next_change, self.tick_variable, args, self)
