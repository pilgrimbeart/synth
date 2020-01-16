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
            pilot : A|B|C|F     # Pilot signal indicates charging state (A=Available, B=finished, C=Charging, F=fault)
            energy:         # kWh transferred so far this session
            uui :           # Charging session token: a random number for each charging session
    }

"""
import logging
import random
from .helpers import opening_times as opening_times

from .device import Device

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24

AVERAGE_CHARGES_PER_DAY = 1.0
CHARGE_POLL_INTERVAL_S = 5 * MINS

CHARGE_RATES_KW_PERCENT = [ [3,  30],
                            [7,  50],
                            [22, 20] ]

MAX_KWH_PER_CHARGE = 70
AVERAGE_HOG_TIME_S = 1 * HOURS

class Charger(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Charger,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.set_property("device_type", "charger")
        self.last_charging_start_time = None
        self.set_property("pilot", "A")
        self.engine.register_event_in(self.delay_to_next_charge(), self.tick_start_charge, self, self)

    def comms_ok(self):
        return super(Charger,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Charger,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Charger,self).close()

    def tick_start_charge(self, _):
        self.uui = random.randrange(0,99999999)
        self.set_properties({
            "pilot" : "C",
            "uui" : self.uui,
            "energy" : 0})
        self.charging_rate = self.choose_charging_rate()
        self.energy_to_transfer = random.random() * MAX_KWH_PER_CHARGE
        self.energy_this_charge = 0
        self.last_charging_start_time = self.engine.get_now()
        logging.info("Start charging at rate "+str(self.charging_rate)+"kW (will transfer "+str(int(self.energy_to_transfer))+"kWh)")
        self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)

    def tick_check_charge(self, _):
        pilot = self.get_property("pilot")
        if pilot == "C":    # Charging
            energy_transferred = (CHARGE_POLL_INTERVAL_S / (60*60)) * self.charging_rate
            self.energy_this_charge += energy_transferred
            self.energy_to_transfer -= energy_transferred
            if self.energy_to_transfer > 0: # Still charging
                self.set_properties({
                    "pilot" : "C",
                    "energy" : int(self.energy_this_charge) })
            else:   # Finished charging
                logging.info("Finished charging")
                self.set_properties({
                    "pilot" : "B",
                    "energy" : int(self.energy_this_charge) })
                self.time_finished_charging = self.engine.get_now()
                self.will_hog_for = random.random() * AVERAGE_HOG_TIME_S
                logging.info("Will hog for "+str(int(self.will_hog_for))+"s or until next charge due")

            self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)
        elif pilot == "B": # Finished charging, still connected
            if self.delay_to_next_charge() <= 0:
                self.tick_start_charge(0)            # Start charging
            else:
                if self.engine.get_now() >= self.time_finished_charging + self.will_hog_for:
                    logging.info("Disconnect")
                    self.set_properties({
                        "pilot" : "A",
                        "energy" : 0})  # Disconnect
                    self.engine.register_event_in(self.delay_to_next_charge(), self.tick_start_charge, self, self)
                else:
                    # logging.info("Hogging for a further "+str(self.engine.get_now() - (self.time_finished_charging + self.will_hog_for)))
                    self.set_properties({
                        "pilot" : "B",
                        "energy" : int(self.energy_this_charge)
                        })
                    self.engine.register_event_in(CHARGE_POLL_INTERVAL_S, self.tick_check_charge, self, self)
        else:
            logging.warning("Unexpected pilot state "+str(pilot))

 
    def delay_to_next_charge(self):
        last = self.last_charging_start_time
        if last is None:
            last = self.engine.get_now()

        nominal = DAYS/AVERAGE_CHARGES_PER_DAY
        interval = random.expovariate(1.0/nominal)
        interval = min(interval, nominal * 10)

        next = last + interval
        delay = next - self.engine.get_now()
        delay = max(0, delay)

        # logging.info("Delay until start of next charge is "+str(delay/(60*60))+" hours")
        return delay

    def choose_charging_rate(self):
        percent = random.randrange(0, 100)
        choice = 0
        cum_likelihood = 0
        while True:
            rate,likelihood = CHARGE_RATES_KW_PERCENT[choice]
            cum_likelihood += likelihood
            if percent <= cum_likelihood:
                break
            choice += 1
        return rate
