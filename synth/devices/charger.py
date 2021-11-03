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
            pilot : A|B|C|F # Pilot signal indicates charging state (A=Available, B=finished, C=Charging, F=fault)
            energy:         # kWh transferred so far this session (ramp which rises)
            power:          # instantaneous kW
            uui :           # Charging session token: a random number for each charging session
            max_kW :        # Max charging power
            monthly_value:  # Approx monthly value of charger
    }

"""
import logging
import random
import isodate
from .helpers import opening_times as opening_times
from common import utils
from .device import Device

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24

DEFAULT_AVERAGE_CHARGES_PER_DAY = 1.0
DEFAULT_AVERAGE_HOG_TIME = "PT1H"

CHARGE_POLL_INTERVAL_S = 5 * MINS

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

HEARTBEAT_PERIOD = 15 * MINS

POWER_TO_MONTHLY_VALUE = 8 # Ratio to turn charger's max kW into currency

FAULTS = [
#       Fault               MTBF        FRACTIONAL DECREASE BASED ON LOCATION
        ["Earth Relay",     100 * DAYS, 0.50],
        ["Mennekes Fault",  200 * DAYS, 0.30],
        ["Overcurrent",     40 * DAYS,  0.00],
        ["RCD trip",        30 * DAYS,  0.00],
        ["Relay Weld",      500 * DAYS, 0.00],
        ["Overtemperature", 300 * DAYS, 0.40]
        ]
FAULT_RECTIFICATION_TIME_AV = 3 * DAYS


ALT_FAULT_CODES = { # Some chargers emit different fault codes
    "Earth Relay" : 100,
    "Mennekes Fault" : 200,
    "Overcurrent" : 300,
    "RCD trip" : 400,
    "Relay Weld" : 500,
    "Overtemperature" : 600
}

class Charger(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Charger,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.loc_rand = utils.consistent_hash(self.get_property_or_None("address_postal_code")) # Allows us to vary behaviour based on our location
        self.opening_time_pattern = opening_times.pick_pattern(self.loc_rand)
        self.set_property("device_type", "charger")
        self.set_property("email", self.get_property("address_postal_code").replace(" ","") + "@example.com")
        sevendigits = "%07d" % int(self.loc_rand * 1E7)
        self.set_property("phone", "+1" + sevendigits[0:3] + "555" + sevendigits[3:7])
        max_rate = self.choose_percent(CHARGER_MAX_RATE_PERCENT)
        self.set_property("max_kW", max_rate)
        self.set_property("monthly_value", max_rate * POWER_TO_MONTHLY_VALUE)
        self.average_charges_per_day = params["charger"].get("average_charges_per_day", DEFAULT_AVERAGE_CHARGES_PER_DAY)
        self.average_hog_time_s = isodate.parse_duration(params["charger"].get("average_hog_time", DEFAULT_AVERAGE_HOG_TIME)).total_seconds()

        self.last_charging_start_time = None
        self.set_properties( {
            "pilot" : "A",
            "energy" : 0,
            "energy_delta" : 0,
            "power" : 0,
            "fault" : None
            })

        self.engine.register_event_in(HEARTBEAT_PERIOD, self.tick_heartbeat, self, self)
        self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)

    def comms_ok(self):
        return super(Charger,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Charger,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Charger,self).close()
    
    def pick_a_fault(self, sampling_interval_s):
        for (fault, mtbf, var) in FAULTS:
            var *= self.loc_rand    # 0..1 based on location
            mtbf = mtbf * (1-var)   # Decrease MTBF by var (i.e. make it less reliable)
            chance = sampling_interval_s / mtbf # 50% point
            if random.random() < chance * 0.5:
                if self.get_property("max_kW") == 50:   # 50kW chargers report different error codes (example of a real-world bizarreness)
                    fault = ALT_FAULT_CODES[fault]
                return fault
        return None

    def tick_heartbeat(self, _):
        self.set_properties({
            "heartbeat" : True
            })
        self.engine.register_event_in(HEARTBEAT_PERIOD, self.tick_heartbeat, self, self)

    def tick_start_charge(self, _):
        # Faulty points can't charge
        if self.get_property("fault") != None:
            self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
            return

        self.uui = random.randrange(0,99999999)
        rate = self.choose_percent(CHARGE_RATES_KW_PERCENT) # What rate would car like to charge?
        rate = min(rate, self.get_property("max_kW"))       # Limit to charger capacity
        self.charging_rate_kW = rate
        self.energy_to_transfer = random.random() * MAX_KWH_PER_CHARGE
        self.energy_this_charge = 0
        self.last_charging_start_time = self.engine.get_now()
        self.set_properties({
            "pilot" : "C",
            "uui" : self.uui,
            "energy" : 0,
            "energy_delta" : 0,
            "power" : self.charging_rate_kW,
            "fault" : None
            })
        self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)

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
            logging.info(str(self.get_property("$id")) + " " + str(fault) + " fault while charging")
            self.set_properties({
               "pilot" : "F",
               "fault" : fault,
               "energy" : 0,
               "energy_delta" : 0,
               "power" : 0
               })
            self.engine.register_event_in(random.random() * FAULT_RECTIFICATION_TIME_AV * 2, self.tick_rectify_fault, self, self)
        else:
            if self.energy_to_transfer > 0: # Still charging
                self.set_properties({
                    "pilot" : "C",
                    "energy" : int(self.energy_this_charge),
                    "energy_delta" : energy_transferred,
                    "power" : self.charging_rate_kW })
                self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)
            else:   # Finished charging
                self.set_properties({
                    "pilot" : "B",
                    "energy" : int(self.energy_this_charge),
                    "energy_delta" : 0,
                    "power" : 0})
                self.time_finished_charging = self.engine.get_now()
                self.will_hog_for = random.random() * self.average_hog_time_s
                self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_blocking, self, self)

    def tick_check_blocking(self, _):
        if self.should_charge_at(self.engine.get_now()):
            self.tick_start_charge(0)            # Start charging
        else:
            if self.engine.get_now() >= self.time_finished_charging + self.will_hog_for:
                self.set_properties({
                    "pilot" : "A",
                    "energy" : 0})  # Disconnect
                self.engine.register_event_at(self.time_of_next_charge(), self.tick_start_charge, self, self)
            else:
                self.set_properties({
                    "pilot" : "B",
                    "energy" : int(self.energy_this_charge)
                    })
                self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_blocking, self, self)
 
    def tick_rectify_fault(self, _):
        logging.info(str(self.get_property("$id")) + " fault rectified")
        self.set_properties({
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
#        interval = random.expovariate(1.0/nominal)
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
        return chance > random.random()

    def time_of_next_charge(self):
        last = self.last_charging_start_time or self.engine.get_now()

        while True: # Keep picking plausible charging times, and use opening_times to tell us how likely each is, until we get lucky
            nominal = DAYS / self.average_charges_per_day
            interval = random.expovariate(1.0/nominal)
            interval = min(interval, nominal * 10)
            interval *= opening_times.average_occupancy()   # Rescale interval to compensate for the average likelihood of opening_times() returning True (so on average we'll hit our target number of charges per day)
            t0 = last + interval
            if self.should_charge_at(t0):
                t0 = max(t0, self.engine.get_now()) # Never choose times in the past
                return t0
            last = t0


    def choose_percent(self, table):
        percent = random.randrange(0, 100)
        choice = 0
        cum_likelihood = 0
        while True:
            rate,likelihood = table[choice]
            cum_likelihood += likelihood
            if percent <= cum_likelihood:
                break
            choice += 1
        return rate
