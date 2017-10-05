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
        "sigmas" :      [a,corresponding,set,of,      standard-deviations] (optional, e.g. "PT1H" means the period will vary randomly with 1 standard deviation of 1 hour)
    }

Device properties created::

    {
        "<name>" : the output property
    }

"""


from device import Device
import random
import isodate
import logging

class Enumerated(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        """Create a property with enumerated events"""
        super(Enumerated, self).__init__(instance_name, time, engine, update_callback, context, params)
        p = params["enumerated"]
        self.enumerated_name = p["name"]
        self.enumerated_values = p["values"]
        self.enumerated_periods = p["periods"]
        self.enumerated_sigmas = p.get("sigmas", None)

        assert len(self.enumerated_values)==len(self.enumerated_periods), "In enumerated device specification, number of periods must match number of values"
        if self.enumerated_sigmas is not None:
            assert len(self.enumerated_values)==len(self.enumerated_sigmas), "In enumerated device specification, number of sigmas must match number of values"

        # Convert to seconds
        for i in range(len(self.enumerated_values)):
            self.enumerated_periods[i] = isodate.parse_duration(self.enumerated_periods[i]).total_seconds()
            if self.enumerated_sigmas is not None:
                self.enumerated_sigmas[i] = isodate.parse_duration(self.enumerated_sigmas[i]).total_seconds()

        for i in range(len(self.enumerated_values)):
            self.schedule_next_event(i)

    def schedule_next_event(self, index):
        period = self.enumerated_periods[index]
        sigma = 0
        if self.enumerated_sigmas:
            sigma = self.enumerated_sigmas[index]
        dt = random.normalvariate(period, sigma)
        dt = min(dt, period + 2*sigma)
        dt = max(dt, period - 2*sigma)
        dt = max(dt, 1.0)   # Ensure we never create negative durations
        self.engine.register_event_in(dt, self.change_enumerated_value, index)

    def change_enumerated_value(self, index):
        self.set_property(self.enumerated_name, self.enumerated_values[index])
        self.schedule_next_event(index)
