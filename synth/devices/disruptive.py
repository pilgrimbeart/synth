"""
disruptive
=====
Simulates sensors from Disruptive Technologies.
By default they pair-up in "sites"

Configurable parameters::

    {
        "sensor_type" : (optional) one of [ccon, temperature, proximity, touch] - if not set then automatically chooses (temperature, proximity) alternately
        "site_prefix" : (optional)      "Fridge "#
        "send_network_status" : False   Disruptive sensors send a lot of these messages
        "nominal_temp" : (optional) for temperature sensors, what the nominal temp is supposed to be, e.g. -18 for a freezer. If it's an array, then chosen randomly. Created as a property too, so DP can do filters relative to it
        "nominal_temp_deviation" : (optional) the normal deviation of the temperature (choice matches above)
        "cooling_MTBF" : (optional) mean time between failure of cooling, for temperature devices, specified as ISO8601 period (e.g. "P100D" means that on average every fridge will fail every 100 days)
        "cooling_TTF" : (optional) mean time to fix a cooling failure
        "site_type" : (optional) a string or list which matches choice above
    }

Device properties created::

    {
        "sensorType" : one of      [ccon, temperature, proximity, touch]
        "signalStrengthCellular" :   y                                    0..100
        "signalStrengthSensor" :               y           y        y
        "state" :                                          y              PRESENT | NOT_PRESENT
        "temperature" :                        y                          degrees C (0.00,0.05) every 15m
        "transmissionMode" :                   y           y        y     HIGH_POWER_BOOST_MODE | LOW_POWER_STANDARD_MODE
        "eventType" :                1         2           2        2     1="cellularStatus" every 5m  2="networkStatus" every 15m
        "connection" :               y                                    CELLULAR | OFFLINE

        "site"  # A site is something like a room, or a fridge, around which multiple devices can exist, whose behaviour is correlated (this only gets created if this device is not part of a model)
    }


    sensorType                     eventType              other properties
    ----------                     ---------              ----------------
    ccon
        every 5m                   "cellularStatus"       "signalStrengthCellular": 10
        when goes offline/online   "connectionStatus"     "connection" : CELLULAR|OFFLINE

    temperature/proximity/touch
        once a day                  batteryStatus         "batteryPercentage" : 100      
        every 15m                   networkStatus         "signalStrengthSensor": 0..100, "

    +temperature
        every 15m                   temperature           "temperature" : 22.5

    +proximity
        when changed                objectPresent         "state" : "PRESENT|NOT_PRESENT"     

    +touch
                                    touch 

    (interestingly, DT's temperature and proximity sensors both also report touch events, but we ignore that here)

"""
import random
import logging
import time
import isodate
from math import sin, pi

from device import Device
from helpers.solar import solar
import device_factory
import helpers.opening_times

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24 

CELLULAR_INTERVAL    = 5 * MINS
NETWORK_INTERVAL     = 15 * MINS
TEMPERATURE_INTERVAL = 15 * MINS
BATTERY_INTERVAL     = 1 * DAYS

DEFAULT_NOMINAL_TEMP_C = -18
EXTERNAL_TEMP_C = 20
TEMP_COUPLING = 0.02    # How quickly internal temperature adapts to external temperature (this happens asymptotically, i.e. as TEMP_COUPLING fraction of the difference per TEMPERATURE_INTERVAL)
DEFAULT_TEMP_DEVIATION = 2

AV_DOOR_OPEN_MIN_TIME_S = 1 * MINS
AV_DOOR_OPEN_SIGMA_S = 2 * MINS
AV_DOOR_OPENS_PER_HOUR = 4
CHANCE_OF_DOOR_LEFT_OPEN = 500  # 1 in N openings causes door to be left open for a LONG time

#      0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20  21  22  23  <- HOURS OF DAY
Mon = [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
Tue = [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
Wed = [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
Thu = [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
Fri = [0,  0,  0,  0,  0,  0,  0,  0,  1,  9,  7,  7,  5,  7,  6,  5,  6,  7,  1,  0,  0,  0,  0,  0] 
Sat = [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
Sun = [0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]

normal_office_hours = [Mon, Tue, Wed, Thu, Fri, Sat, Sun]

def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    assert False, "Shouldn't get here"

def half_tail(min, sigma):
    while True:
        r = random.gauss(min, sigma)
        if (r >= min) and (r < min * 10.0): # Select only positive half of gaussian distribution (and remove outliers beyond 10x the mean)
            return r

def cyclic_noise(id,t):    # Provides a somewhat cyclic (not completely stochastic) noise of +/- 0.5
    t = float(t + hash(id)) * 2 * pi    # a cycle every second, until divided
    return (sin(t/(MINS*7.5)) + sin(t/(HOURS*3.5)) + sin(t/DAYS) + sin(t/(DAYS*3)) + sin(t/(DAYS*7)) + sin(t/(DAYS*30)) + sin(t/(DAYS*47))) / (7*2) 

class Disruptive(Device):
    site_count = 1
    odd_site = False
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Disruptive,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.sensor_type = params["disruptive"].get("sensor_type", None)
        self.site_prefix = params["disruptive"].get("site_prefix", "Fridge ")
        if params["disruptive"].get("site_prefix", None) is not None:
            self.set_property("site", self.site_prefix + str(Disruptive.site_count))    # This mechanism is superceded now by Models and should be removed
        if self.sensor_type is None:
            if not Disruptive.odd_site: # Alternate type
                self.sensor_type = "temperature"
            else:
                self.sensor_type = "proximity"
            # self.sensor_type = weighted_choice([("ccon",5), ("temperature",38), ("proximity",33), ("touch",2)])
        self.set_property("sensorType", self.sensor_type)           # DT's official property for sensor type
        self.set_property("device_type", "DT_"+self.sensor_type)    # In DP demos we tend to use this property

        if(self.sensor_type != "ccon"):
            engine.register_event_in(BATTERY_INTERVAL, self.tick_battery, self, self)
            if(params["disruptive"].get("send_network_status", False)):
                engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)
        if(self.sensor_type == "ccon"):
            engine.register_event_in(CELLULAR_INTERVAL, self.tick_cellular, self, self)
        if(self.sensor_type == "temperature"):
            self.nominal_temperature = params["disruptive"].get("nominal_temp", DEFAULT_NOMINAL_TEMP_C)
            if isinstance(self.nominal_temperature, list):
                choice = random.randint(0,len(self.nominal_temperature)-1)
                self.nominal_temperature = self.nominal_temperature[choice]
            if "nominal_temp" in params["disruptive"]:
                self.set_property("nominal_temp", self.nominal_temperature)
            self.set_temperature(self.nominal_temperature)
            self.temperature_deviation = params["disruptive"].get("nominal_temp_deviation", DEFAULT_TEMP_DEVIATION)
            if isinstance(self.temperature_deviation, list):
                self.temperature_deviation = self.temperature_deviation[choice] # Matches temp choice above
            if "site_type" in params["disruptive"]:
                site_type = params["disruptive"]["site_type"][choice]
                self.set_property("site_type", site_type)
            engine.register_event_in(TEMPERATURE_INTERVAL, self.tick_temperature, self, self)
            self.having_cooling_failure = False
        if(self.sensor_type == "proximity"):
            self.set_property("objectPresent", "PRESENT")   # Door starts closed
            self.schedule_next_presence_event()

        self.cooling_mtbf = params["disruptive"].get("cooling_mtbf", None)
        if self.cooling_mtbf:
            self.cooling_mtbf = isodate.parse_duration(self.cooling_mtbf).total_seconds()
        self.cooling_ttf = isodate.parse_duration(params["disruptive"].get("cooling_TTF", "P3D")).total_seconds()

        Disruptive.odd_site = not Disruptive.odd_site
        if not Disruptive.odd_site:
            Disruptive.site_count += 1

    def comms_ok(self):
        return super(Disruptive,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Disruptive,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Disruptive,self).close()

    # Private methods
    def tick_battery(self, _):
        self.set_property("eventType", "batteryPercentage", always_send=True)
        self.set_property("batteryPercentage", 100, always_send=True)
        self.engine.register_event_in(BATTERY_INTERVAL, self.tick_battery, self, self)

    def tick_network(self, _):
        self.set_property("eventType", "networkStatus", always_send=True)
        self.set_property("signalStrengthSensor", 100, always_send=True)
        self.engine.register_event_in(NETWORK_INTERVAL, self.tick_network, self, self)

    def tick_cellular(self, _):
        self.set_property("eventType", "cellularStatus", always_send=True)
        self.set_property("signalStrengthCellular", 100, always_send=True)
        self.engine.register_event_in(CELLULAR_INTERVAL, self.tick_cellular, self, self)

    def tick_temperature(self, _):
        # Check for cooling failure
        if self.cooling_mtbf is not None:
            if not self.having_cooling_failure:
                chance_of_cooling_failure = float(TEMPERATURE_INTERVAL) / self.cooling_mtbf
                if random.random() < chance_of_cooling_failure:
                    logging.info("Cooling failure on device "+str(self.get_property("$id")))
                    self.having_cooling_failure = True
            else:
                chance_of_failure_ending = TEMPERATURE_INTERVAL / self.cooling_ttf
                if random.random() < chance_of_failure_ending:
                    logging.info("Cooling failure fixed on device "+str(self.get_property("$id")))
                    self.having_cooling_failure = False

        # Check for door open
        door_open = False
        peers = self.get_peers()
        if len(peers)==1:   # Currently we can only cope with one peer in the model (1 proximity and 1 temperature)"
            peer = peers[0]
            if peer.property_exists("objectPresent"):
                door_open = peer.get_property("objectPresent") == "NOT_PRESENT"

        temp = self.get_temperature()

        if door_open or self.having_cooling_failure:
            temp = temp * (1.0 - TEMP_COUPLING) + (EXTERNAL_TEMP_C * TEMP_COUPLING)
        else:
            temp = self.nominal_temperature + cyclic_noise(self.get_property("$id"), self.engine.get_now()) * self.temperature_deviation

        self.set_temperature(temp)
        self.engine.register_event_in(TEMPERATURE_INTERVAL, self.tick_temperature, self, self)

    def tick_presence(self, _):
        if self.get_property("objectPresent")=="PRESENT":   # Door currently closed
            self.set_property("objectPresent", "NOT_PRESENT")
        else:
            self.set_property("objectPresent", "PRESENT")
        self.schedule_next_presence_event()

    def schedule_next_presence_event(self):
        if self.get_property("objectPresent") == "PRESENT": # Door just closed, so consider when it should next open
            # Work-out when door should next open by exploring each hour (from current hour), with chance of door opening in that hour being set according to lookup table. If not open then keep moving forwards.
            t = time.gmtime(self.engine.get_now())   # Should be localised using lat/lon if available
            weekday = t.tm_wday  # Monday is 0
            hour = t.tm_hour + t.tm_min/60.0
            delta_hours = 0.0
            while True:
                # Explore next time period
                delta_hours += 1.0/AV_DOOR_OPENS_PER_HOUR
                hour += 1.0/AV_DOOR_OPENS_PER_HOUR
                if hour >= 24:
                    hour -= 24
                    weekday = (weekday + 1) % 7
                # logging.info("tick_presence considering weekday="+str(weekday)+" hour="+str(hour))
                chance_of_opening = normal_office_hours[weekday][int(hour)]/9.0  # Rescale 0..9 to 0..1
                if random.random() <= chance_of_opening:
                    break
            self.engine.register_event_in(delta_hours*60*60, self.tick_presence, self, self)
        else:   # Door just opened, so consider when it should next close
            if random.random() < 1.0/CHANCE_OF_DOOR_LEFT_OPEN:
                delay = half_tail(1 * HOURS, 24 * HOURS)
                logging.info("Door will be left open for "+str(int(delay/60))+"m on "+str(self.get_property("$id")))
            else:
                delay = half_tail(AV_DOOR_OPEN_MIN_TIME_S, AV_DOOR_OPEN_SIGMA_S)
            self.engine.register_event_in(delay, self.tick_presence, self, self)

    def get_peers(self):
        if self.model:  # If we're running in a model, then use that to find our peers
            return self.model.get_peers(self)
        else:   # Otherwise default to our own inbuilt peer-finding mechanism
            logging.info("USING INBUILT MODEL TO FIND PEER")
            site = self.get_property("site", None)
            if site is None:
                return None
            me = self.get_property("$id")
            peer = None
            peers = device_factory.get_devices_by_property("site", site)    # All devices at this site
            for p in peers:
                if p.get_property("$id") != me:
                    peer = p
            return [peer]

    def set_temperature(self, temperature):  # Temperature stored internally to higher precision than reported (so we can do e.g. asymptotes) 
        self.temperature = temperature
        self.set_property("eventType", "temperature", always_send=True)
        temp = int(temperature * 10) / 10.0
        self.set_property("temperature", temp, always_send=True)

    def get_temperature(self):
        return self.temperature

