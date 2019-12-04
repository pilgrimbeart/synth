"""
cluster
=====
Simulates sites which are clusters, e.g. bike/scooter sharing docs, multiple charging points on a single site,
A device is a cluster. Each cluster has a number of "slots", each of which are available/unavailable at any moment in time, giving rise to a total number of used/available slots.

Configurable parameters::

    {
            "min_slots_per_cluster" : 4,
            "max_slots_per_cluster" : 32
    }

Device properties created::

    {
        <TODO>
    }

"""


from .device import Device
import helpers.opening_times as opening_times
import random
import isodate
import logging

MINUTES = 60
HOURS = 60*60
DAYS = HOURS*24

TICK_INTERVAL_S = 15 * MINUTES

DEFAULT_MIN_SLOTS_PER_CLUSTER   = 4
DEFAULT_MAX_SLOTS_PER_CLUSTER   = 32
DEFAULT_OCCUPANCY_PATTERN = "rushhour"
DEFAULT_OCCUPANCY_RANDOMNESS = 0.3
DEFAULT_TIME_SKEW_RANDOMNESS = 3 * HOURS

class Cluster(Device):
    myRandom = random.Random()  # Use our own private random-number generator, so we will repeatably generate the same device ID's regardless of who else is asking for random numbers
    myRandom.seed(1234)
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Cluster,self).__init__(instance_name, time, engine, update_callback, context, params)
        min_slots = params["cluster"].get("min_slots_per_cluster", DEFAULT_MIN_SLOTS_PER_CLUSTER)
        max_slots = params["cluster"].get("max_slots_per_cluster", DEFAULT_MAX_SLOTS_PER_CLUSTER)
        self.occupancy_pattern = params["cluster"].get("occupancy_pattern", DEFAULT_OCCUPANCY_PATTERN)
        self.occupancy_randomness = params["cluster"].get("occupancy_randomness", DEFAULT_OCCUPANCY_RANDOMNESS)
        time_skew_randomness = params["cluster"].get("time_skew_randomness", DEFAULT_TIME_SKEW_RANDOMNESS)
        self.num_slots = Cluster.myRandom.randrange(min_slots, max_slots)
        self.time_skew = time_skew_randomness / 2.0 + Cluster.myRandom.random() * time_skew_randomness / 2.0
        self.available_slots = self.calc_occupancy()
        self.set_properties({"num_slots" : self.num_slots, "available_slots" : self.available_slots})

        engine.register_event_in(TICK_INTERVAL_S, self.tick_availability, self, self)

    def comms_ok(self):
        return super(Cluster,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Cluster,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Cluster,self).close()

    # Private methods

    def tick_availability(self, _):
        self.available_slots = self.calc_occupancy()
        self.set_property("available_slots", self.available_slots)
        self.engine.register_event_in(TICK_INTERVAL_S, self.tick_availability, self, self)

    def calc_occupancy(self):
        occupancy = opening_times.chance_of_occupied(self.engine.get_now() + self.time_skew, self.occupancy_pattern)
        occupancy = occupancy - self.occupancy_randomness / 2.0 + Cluster.myRandom.random() * self.occupancy_randomness / 2.0
        return occupancy


