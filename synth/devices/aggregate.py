"""
Aggregate
=====
Aggregates properties within the model

Configurable parameters::

    {
            "numbers" : ["name","name", ...]  # Names of numeric properties to be averaged
            "booleans" : ["name", "name", ...]  # Ditto for boolean properties
    }

Device properties created::

    {
            (whatever properties it finds)
    }
"""
import logging
import time

from device import Device

POLL_INTERVAL_S = 60 * 15

class Aggregate(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Aggregate,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.set_property("device_type", "aggregate")
        self.engine.register_event_in(POLL_INTERVAL_S, self.tick_aggregate, self, self)
        self.numbers_to_aggregate = params["aggregate"].get("numbers", [])
        self.booleans_to_aggregate = params["aggregate"].get("booleans", [])

    def comms_ok(self):
        return super(Aggregate,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Aggregate,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Aggregate,self).close()

    # Private methods

    def do_aggregation(self):
        # logging.info("Doing aggregation for device "+str(self.get_property("$id") + " " + str(self.model_spec)))
        # logging.info("Looking for "+str(self.numbers_to_aggregate) + " and "+str(self.booleans_to_aggregate))
        devices = self.model.get_peers_and_below(self)
        numbers = {}  # A set of lists, one for each property type of interest
        booleans = {}  # A set of lists, one for each property type of interest
        for d in devices:
            new_props = d.get_properties()
            for p in new_props:
                # logging.info("Considering property "+str(p))
                if p in self.numbers_to_aggregate:
                    # logging.info("Aggregating number "+str(p))
                    if p in numbers:
                        numbers[p].append(new_props[p])
                    else:
                        numbers[p] = [new_props[p]]
                if p in self.booleans_to_aggregate:
                    # logging.info("Aggregating boolean "+str(p))
                    if p in booleans:
                        booleans[p].append(new_props[p])
                    else:
                        booleans[p] = [new_props[p]]
        # logging.info("Numbers: "+str(numbers))
        # logging.info("Booleans: "+str(booleans))
        # Now aggregate
        for p in numbers:
            result = 0.0
            for n in numbers[p]:
                result += n
            result /= len(numbers[p])
            # logging.info("set property "+str(p)+" = "+str(result))
            self.set_property(p+"_average", result)

        for p in booleans:
            result = 0.0
            for n in booleans[p]:
                if n:
                    result += 1.0
            result /= float(len(booleans[p]))
            # logging.info("set property "+str(p)+" = "+str(result))
            self.set_property(p+"_average", result)


    def tick_aggregate(self, _):
        self.do_aggregation()
        self.engine.register_event_in(POLL_INTERVAL_S, self.tick_aggregate, self, self)

