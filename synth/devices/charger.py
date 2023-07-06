"""
charger
=====
Simulates a charging system (e.g. EV-charging, battery charging)

Configurable parameters::

    {
            <TODO>
    }

Device properties created::

    {
            pilot : A|B|C|F # Pilot signal indicates charging state (A=Available, B=Blocking, C=Charging, F=Fault)
            energy:         # kWh transferred so far this session (ramp which rises)
            power:          # instantaneous kW
            uui :           # Charging session token: a random number for each charging session
            max_kW :        # Max charging power
            monthly_value:  # Approx monthly value of charger
            occupied:       # True when there is a vehicle present (which may be ICE in which case no charge cycle will occur)
    }

There are three things that can get in the way of charging:
    1) Hogging - a car finishes charging (Pilot goes C->B) and just stays there
    2) Fault - a charger goes into a fault state
    3) ICEing - a car arrives in the spot (occupied==True) but doesn't start charging.

"""
import logging
import time
import random
import isodate
import datetime
from .helpers import opening_times as opening_times
from .helpers import ev_mfrs as ev_mfrs
from common import utils
from .device import Device

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24

MAX_INTERVAL_BETWEEN_POTENTIAL_CHARGES_S = 10 * HOURS   # Not precise, but smaller means more charging
DEFAULT_AVERAGE_BLOCKING_TIME = "PT60M"
CHANCE_OF_BLOCKING = 0.2                                # If this is close to 1, implies that cars often charge to full.
CHANCE_OF_ZERO_ENERGY_CHARGE = 0.01 
CHANCE_OF_SILENT_FAULT = 0.005                          # A silent fault is one that isn't flagged with a fault code, but nevertheless prevents charging (e.g. external damage)

CHARGE_POLL_INTERVAL_S = 5 * MINS

MIN_GAP_BETWEEN_CHARGES_S = 10 * MINS

CHARGER_MAX_RATE_PERCENT = [ [7, 20],
                             [22, 40],
                             [50, 20],
                             [100, 10],
                             [150, 10] ]

CHARGE_RATES_KW_PERCENT = [ [3,  10],
                            [7,  30],
                            [22, 30],
                            [50, 20],
                            [100,5],
                            [150,5] ]

MAX_KWH_PER_CHARGE = 70
DWELL_TIME_MIN_S = 20 * MINS
DWELL_TIME_MAX_S = 8 * HOURS
DWELL_TIME_AV_S = 1 * HOURS
KWH_PER_CHARGE_MIN = 4
KWH_PER_CHARGE_MAX = 70
KWH_PER_CHARGE_AV = 20


HEARTBEAT_PERIOD = 5 * MINS

POWER_TO_MONTHLY_VALUE = 8 # Ratio to turn charger's max kW into currency

FAULTS = [
#       Fault               MTBF        FRACTIONAL DECREASE BASED ON LOCATION
        ["Earth Relay",     20 * DAYS, 0.50],
        ["Mennekes Fault",  40 * DAYS, 0.30],
        ["Overcurrent",     15 * DAYS,  0.00],
        ["RCD trip",        20 * DAYS,  0.00],
        ["Relay Weld",      100 * DAYS, 0.00],
        ["Overtemperature", 100 * DAYS, 0.40]
        ]
FAULT_RECTIFICATION_TIME_AV = 2 * DAYS


ALT_FAULT_CODES = { # Some chargers emit different fault codes
    "Earth Relay" : 100,
    "Mennekes Fault" : 200,
    "Overcurrent" : 300,
    "RCD trip" : 400,
    "Relay Weld" : 500,
    "Overtemperature" : 600
}

VOLTAGE_FAULT = "Voltage excursion"
MAX_SAFE_VOLTAGE = 253
MIN_SAFE_VOLTAGE = 207

CHANCE_OF_ICEING = 0.02  # For any intended charge cycle, what is the chance that instead someone blocks the charger with a fossil-fuel car (i.e. "occupied" but no charge)

class Charger(Device):
    myRandom = random.Random()  # Use our own private random-number generator for repeatability
    myRandom.seed(5678)

    def expo_random(self, min_val, max_val, av_val):
        n = Charger.myRandom.expovariate(1/av_val)
        n = min(max_val, n)
        n = max(min_val, n)
        return n

    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Charger,self).__init__(instance_name, time, engine, update_callback, context, params)
        if self.property_exists("address_postal_code"):
            self.loc_rand = utils.consistent_hash(self.get_property_or_None("address_postal_code")) # Allows us to vary behaviour based on our location
            domain = self.get_property("address_postal_code").replace(" ","") + ".example.com"
        else:
            self.loc_rand = utils.consistent_hash(self.get_property("$id"))
            domain = "example.com"
        self.set_property("domain", domain)

        (mfr,model,max_rate,datasheet) = ev_mfrs.pick_mfr_model_kW_datasheet(self.loc_rand)
        self.set_properties_with_metadata( {
            "manufacturer" : mfr,
            "model" : model,
            "max_kW" : max_rate,
            "datasheet" : datasheet,
            "monthly_value" : max_rate * POWER_TO_MONTHLY_VALUE * Charger.myRandom.random() * 2
        } )

        self.opening_time_pattern = opening_times.pick_pattern(self.loc_rand)
        self.set_property("opening_times", opening_times.specification(self.opening_time_pattern))
        self.set_property("device_type", "charger") 
        self.set_property("email", self.get_property("$id") + "@" + domain)
        sevendigits = "%07d" % int(self.loc_rand * 1E7)
        self.set_property("phone", "+1" + sevendigits[0:3] + "555" + sevendigits[3:7])
        self.set_property("occupied", False)
        self.average_blocking_time_s = isodate.parse_duration(params["charger"].get("average_blocking_time", DEFAULT_AVERAGE_BLOCKING_TIME)).total_seconds()

        self.last_charging_start_time = None
        self.last_charging_end_time = None
        self.set_properties_with_metadata( {
            "pilot" : "A",
            "energy" : 0,
            "energy_delta" : 0,
            "power" : 0,
            "fault" : None
            })
        self.silent_fault = False

        self.engine.register_event_in(HEARTBEAT_PERIOD, self.tick_heartbeat, self, self)
        self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)

    def comms_ok(self):
        return super(Charger,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Charger,self).external_event(event_name, arg)
        logging.info("Handling external event for "+str(self.properties["$id"]))
        if event_name=="resetVoltageExcursion":
            logging.info("Resetting voltage excursion on device "+self.properties["$id"])
            self.set_properties_with_metadata({
                    "pilot" : "A",
                    "fault" : None
                    })
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
        else:
            logging.error("Ignoring unrecognised external event "+str(event_name))

    def close(self):
        super(Charger,self).close()
    
    # ---- internal methods
    def metadata(self):
        def hexdigit(n):
            chars = "0123456789abcdef"
            return chars[(utils.consistent_hash_int(myid)+n*12345) % len(chars)]
        myid = self.get_property("$id")
        props = {}
        props["mac_address"] = ""
        for i in range(12):
            props["mac_address"] += hexdigit(i)

        props["metadata.ppid"] = "PSL-" + str(int(utils.consistent_hash_int(myid) % 1E6))
        props["metadata.door"] = "A"
        props["metadata.evseId"] = 1
        props["sn"] = str(int(utils.consistent_hash_int(myid) % 1E10))
        logging.info("metadata for "+myid+" is "+str(props))
        return props

    def set_properties_with_metadata(self, props):
        props.copy()
        props.update(self.metadata())
        self.set_properties(props)

    def pick_a_fault(self, sampling_interval_s):
        for (fault, mtbf, var) in FAULTS:
            var *= self.loc_rand    # 0..1 based on location
            mtbf = mtbf * (1-var)   # Decrease MTBF by var (i.e. make it less reliable)
            chance = sampling_interval_s / mtbf # 50% point
            if Charger.myRandom.random() < chance * 0.5:
                if self.get_property("max_kW") == 50:   # 50kW chargers report different error codes (example of a real-world bizarreness)
                    fault = ALT_FAULT_CODES[fault]
                return fault
        return None

    def tick_heartbeat(self, _):
        self.set_properties_with_metadata({
            "heartbeat" : True,
            "event" : "HEARTBEAT"
            })

        # Go into fault state if voltage outside legal limits
        v = self.get_property("voltage")
        if v is not None:
            if v > MAX_SAFE_VOLTAGE or v < MIN_SAFE_VOLTAGE:
                self.enter_fault_state(VOLTAGE_FAULT)
            
        self.engine.register_event_in(HEARTBEAT_PERIOD, self.tick_heartbeat, self, self)

    def tick_start_charge(self, _):
        # Maybe this is an ICEing, not a charge
        if Charger.myRandom.random() < CHANCE_OF_ICEING:
            self.set_property("occupied", True)
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_end_iceing, self, self) # An iceing takes as long as a charge, let's say
            return

        # Faulty points can't charge
        if self.get_property("fault") != None:
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
            return

        if Charger.myRandom.random() < CHANCE_OF_SILENT_FAULT:    # Start a silent fault
            self.silent_fault = True

        if self.silent_fault:   # For now, silent faults never end
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
            return

        self.uui = (hash(self.get_property("$id")) + hash(time.time())) % int(1E10)  # Needs to be unique even on re-runs of Synth. So we use real (clock) time, not event time (which normally we'd NEVER do in a device behaviour)
        rate = self.choose_percent(CHARGE_RATES_KW_PERCENT) # What rate would car like to charge?
        rate = min(rate, self.get_property("max_kW"))       # Limit to charger capacity
        self.charging_rate_kW = rate
        if Charger.myRandom.random() < CHANCE_OF_ZERO_ENERGY_CHARGE:
            logging.info(self.get_property("$id")+": Starting zero energy charge")
            self.charging_rate_kW = 0 
        self.energy_to_transfer = self.expo_random(KWH_PER_CHARGE_MIN, KWH_PER_CHARGE_MAX, KWH_PER_CHARGE_AV)
        self.max_charging_time_s = self.expo_random(DWELL_TIME_MIN_S, DWELL_TIME_MAX_S, DWELL_TIME_AV_S)
        self.energy_this_charge = 0
        self.last_charging_start_time = self.engine.get_now()
        self.set_properties_with_metadata({
            "pilot" : "C",
            "uui" : self.uui,
            "energy" : 0,
            "energy_delta" : 0,
            "power" : self.charging_rate_kW,
            "fault" : None,
            "occupied" : True
            })
        self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)

    def enter_fault_state(self, fault):
        logging.info(str(self.get_property("$id")) + " " + str(fault) + " fault")
        self.set_properties_with_metadata({
           "pilot" : "F",
           "fault" : fault,
           "energy" : 0,    # We might have been charging so stop charge
           "energy_delta" : 0,
           "power" : 0
           })
        self.engine.register_event_in(Charger.myRandom.random() * FAULT_RECTIFICATION_TIME_AV * 2, self.tick_rectify_fault, self, self)

    def tick_check_charge(self, _):
        # (faults can be externally-injected)
        if self.get_property("fault") != None:
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
            return

        energy_transferred = (CHARGE_POLL_INTERVAL_S / (60*60)) * self.charging_rate_kW
        self.energy_this_charge += energy_transferred
        self.energy_to_transfer -= energy_transferred
        fault = self.pick_a_fault(CHARGE_POLL_INTERVAL_S)    # Faults only occur while charging
        if fault != None: 
            self.enter_fault_state(fault)
        else:
            if (self.energy_to_transfer > 0) and (self.engine.get_now() - self.last_charging_start_time < self.max_charging_time_s):    # STILL CHARGING
                self.set_properties_with_metadata({
                    # "pilot" : "C",
                    "energy" : int(self.energy_this_charge),
                    "energy_delta" : energy_transferred,
                    "power" : self.charging_rate_kW })
                self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)
            else:                                                                   # FINISHED CHARGING
                self.time_finished_charging = self.engine.get_now()
                if Charger.myRandom.random() < CHANCE_OF_BLOCKING:
                    self.will_block_for = Charger.myRandom.random() * self.average_blocking_time_s   # BLOCKING
                    self.set_properties_with_metadata({
                        "pilot" : "B",
                        "energy" : int(self.energy_this_charge),
                        "energy_delta" : 0,
                        "power" : 0})
                    self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_blocking, self, self)
                else:                                                               # AVAILABLE
                    self.set_properties_with_metadata({
                        "pilot" : "A",
                        "occupied" : False,
                        "energy" : 0,
                        "energy_delta" : 0,
                        "power" : 0})
                    tonc = self.time_of_next_charge()
                    self.engine.register_event_at(tonc, self.tick_start_charge, self, self)

    def tick_check_blocking(self, _):
        if self.engine.get_now() >= self.time_finished_charging + self.will_block_for:
            self.set_properties_with_metadata({
                "pilot" : "A",
                "energy" : 0,
                "occupied" : False})  # Disconnect
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
        else:
            self.set_properties_with_metadata({
                "pilot" : "B",
                "energy" : int(self.energy_this_charge)
                })
            self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_blocking, self, self)
 
    def tick_end_iceing(self, _):
        self.set_property("occupied", False)
        self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)

    def tick_rectify_fault(self, _):
        if self.get_property("fault") in [VOLTAGE_FAULT]:  # Some faults don't fix themselves
            return

        self.set_properties_with_metadata({
                "pilot" : "A",
                "fault" : None
                })
        self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)

#    def delay_to_next_charge(self):
#        last = self.last_charging_start_time
#        if last is None:
#            last = self.engine.get_now()
#
#        nominal = DAYS/self.average_charges_per_day
#        interval = Charger.myRandom.expovariate(1.0/nominal)
#        interval = min(interval, nominal * 10)
#
#        next = last + interval
#        delay = next - self.engine.get_now()
#        delay = max(60, delay)
#
#        return delay

    def should_charge_at(self, epoch):
        # Given a time, should we charge at it?
        chance = opening_times.chance_of_occupied(epoch, self.opening_time_pattern)
        yes = chance > Charger.myRandom.random()
        return yes

    def time_of_next_charge(self):
        # last = self.last_charging_start_time or self.engine.get_now() # Why from start? For statistical purity probably, but risks trying to start a charge in the past?
        t0 = self.engine.get_now() + MIN_GAP_BETWEEN_CHARGES_S    # This ASSUMES that we're asking this question at the end of a charge (sometimes at least)

        while True: # Keep picking plausible charging times, and use opening_times to tell us how likely each is, until we get lucky
            if self.should_charge_at(t0):
                return t0
            # nominal = DAYS / self.average_charges_per_day
            # interval = Charger.myRandom.expovariate(1.0/nominal)
            # interval = min(interval, nominal * 10)
            # interval *= opening_times.average_occupancy()   # Rescale interval to compensate for the average likelihood of opening_times() returning True (so on average we'll hit our target number of charges per day)
            # t0 += interval
            t0 += Charger.myRandom.random() * MAX_INTERVAL_BETWEEN_POTENTIAL_CHARGES_S 


    def choose_percent(self, table):
        percent = Charger.myRandom.randrange(0, 100)
        choice = 0
        cum_likelihood = 0
        while True:
            rate,likelihood = table[choice]
            cum_likelihood += likelihood
            if percent <= cum_likelihood:
                break
            choice += 1
        return rate
