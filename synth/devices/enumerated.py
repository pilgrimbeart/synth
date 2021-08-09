"""
enumerated
==========
Creates a property whose value changes between specific enumerated values, with a given probability.
Useful for simulating device events such as lifecycle events and error conditions.

Configurable parameters::

    {
        "name" : property name
        "values" :      [a,set,          of, possible,values]
        "periods" :     [a,corresponding,set,of,      periods] (each is an ISO8601 duration e.g. "P1D" means the event will happen once a day)
        "sigmas" :      [a,corresponding,set,of,      standard-deviations] (optional, e.g. "PT1H" means the period will vary randomly with 1 standard deviation of 1 hour). Otherwise 1/10th of period.
        "always_send" : true (optional)    If true then values will be sent even if they haven't changed
        "force_send" : false (optional)    If true then values will be sent even if device is offline
        "send_timestamp" : false (optional)    If true then a "_ts" property is set to the current epoch_ms whenever the property is changed to a value which is not null.
    }

If sigmas are not specified, they default to 50% of the periods to create a good amount of random spread. If you want to remove all randomness, specify sigmas of "PT0S".


Device properties created::

    {
        "<name>" : the output property
    }

"""


from .device import Device
import random
import isodate
import logging

DEFAULT_SIGMA_RATIO = 0.1   # If no sigma specified, it defaults to this fraction of the period

class Enumerated(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """Create a property with enumerated events"""
        super(Enumerated, self).__init__(instance_name, time, engine, update_callback, context, params)
        p = params["enumerated"]
        self.enumerated_always_send = p.get("always_send", True)
        self.enumerated_force_send = p.get("force_send", False)
        self.enumerated_send_timestamp = p.get("send_timestamp", False)
        self.enumerated_name = p["name"]
        self.enumerated_values = p["values"]
        periods = p["periods"]
        sigmas = p.get("sigmas", None)

        assert len(periods)==len(self.enumerated_values), "In enumerated device specification, number of periods must match number of values"
        if sigmas is not None:
            assert len(sigmas)==len(self.enumerated_values), "In enumerated device specification, number of sigmas must match number of values"

        # Convert to seconds
        self.enumerated_periods = []
        if sigmas is None:
            self.enumerated_sigmas = None
        else:
            self.enumerated_sigmas = []
        for i in range(len(self.enumerated_values)):
            self.enumerated_periods.append(isodate.parse_duration(periods[i]).total_seconds())
            if self.enumerated_sigmas is not None:
                self.enumerated_sigmas.append(isodate.parse_duration(sigmas[i]).total_seconds())

        # Find most likely current state
        recip_periods = [1.0/x for x in self.enumerated_periods]    # The shorter the period, the more likely it is to be the current state]
        total_periods = sum(recip_periods)
        choice = random.random() * total_periods
        so_far = 0
        for i in range(len(self.enumerated_periods)):
            so_far += recip_periods[i]
            if so_far >= choice:
                self.enum_set_value(self.enumerated_values[i], True)
                break
        
        # Schedule next transitions
        for i in range(len(self.enumerated_values)):
            self.schedule_next_event(i)

    def comms_ok(self):
        return super(Enumerated, self).comms_ok()

    def external_event(self, event_name, arg):
        super(Enumerated, self).external_event(event_name, arg)

    def close(self):
        super(Enumerated,self).close()

    def enum_set_value(self, value, first_time = False):
        name = self.enumerated_name
        ts = self.engine.get_now_1000()
        if first_time:
            self.set_property(self.enumerated_name, value)
            if self.enumerated_send_timestamp:
                if value == None:
                    self.set_property(name + "_ts", None)
                else:
                    self.set_property(name + "_ts", ts)
        else:
            self.set_property(name, value, always_send = self.enumerated_always_send, force_send = self.enumerated_force_send)
            if self.enumerated_send_timestamp:
                if value != None:
                    self.set_property(name + "_ts", ts, always_send = self.enumerated_always_send, force_send = self.enumerated_force_send)

    def schedule_next_event(self, index):
        period = self.enumerated_periods[index]
        sigma = 0
        if self.enumerated_sigmas:
            sigma = self.enumerated_sigmas[index]
        else:
            sigma = period * DEFAULT_SIGMA_RATIO
        # logging.info("period = " + str(period) + " sigma = " + str(sigma))

        dt = random.normalvariate(period, sigma)
        dt = min(dt, period + 2*sigma)
        dt = max(dt, period - 2*sigma)
        dt = max(dt, 1.0)   # Ensure we never create negative durations
        #if dt < 60*60*24*30:
        #    logging.info("Registering event "+str(index)+" in "+str(dt))
        self.engine.register_event_in(dt, self.change_enumerated_value, index, self)

    def change_enumerated_value(self, index):
        value = self.enumerated_values[index]
        # logging.info("Changing enumerated value on "+str(self.get_property("$id"))+" to index "+str(index)+" which is "+str(value))
        self.enum_set_value(value)
        self.schedule_next_event(index)

