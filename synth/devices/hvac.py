"""
hvac
=====
Simulates HVAC system in a building, with heating and cooling and inputs like local weather etc.

Configurable parameters::

    {
            opening_times : (optional) "nine_to_five"
            target_temp_ideal : (optional) 21 
            occupied_target_temp_min : (optional) 20
            occupied_target_temp_max : (optional) 22
            unoccupied_target_temp_min : (optional) 16
            unoccupied_target_temp_max : (optional) 28
            kwh_per_degree_day : (optional) 1000
            degrees_change_per_hour : (optional) 5  # How fast heating or cooling can work
    }

Device properties created::

    {
            insolation  # Amount of sunshine 
            external_temperature # Copied from any related weather sensor
            temperature # Internal building temperature
            kW          # Power being used for heating or cooling
            pump_run    # When heating or cooling pumps are running
    }

"""
import random
import logging
import time
from .helpers.solar import solar
from .helpers import opening_times as opening_times

from .device import Device

MINS = 60
HOURS = MINS * 60
DAYS = HOURS * 24

POLL_INTERVAL_S = 15 * MINS
INSOLATION_FORCING_DEGREES = 5  # How many extra degrees of outside temperature full sunlight 
INDOOR_OUTDOOR_COUPLING = 0.02  # How quickly outdoor temperatures affect indoors (without adding energy for heating or cooling)
INDOOR_OUTDOOR_COUPLING_WINDOW_OPEN = 0.5      # Ditto when window open!
PUMP_RUN_ON_S = 30 * MINS
TEMP_HYSTERESIS = 1  # Amount of overshoot allowed on heating & cooling

DEFAULT_KW_PER_C = 10   # How many KW is required to overcome 1 degree of temp difference?
DEFAULT_OPENING_TIMES = "eight_to_six"
DEFAULT_TARGET_TEMP_IDEAL = 21
DEFAULT_TARGET_TEMP_OCCUPIED_MIN = 20
DEFAULT_TARGET_TEMP_OCCUPIED_MAX = 22
DEFAULT_TARGET_TEMP_UNOCCUPIED_MIN = 10 
DEFAULT_TARGET_TEMP_UNOCCUPIED_MAX = 28
DEFAULT_KWH_PER_DEGREE_DAY = 1000 
DEFAULT_DEGREES_CHANGE_PER_HOUR = 5
DEFAULT_RELIABILITY = 1.0

class Hvac(Device):
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Hvac,self).__init__(instance_name, time, engine, update_callback, context, params)
        self.opening_times = params["hvac"].get("opening_times", DEFAULT_OPENING_TIMES)
        self.target_temp_ideal = params["hvac"].get("target_temp_ideal", DEFAULT_TARGET_TEMP_IDEAL)
        self.target_temp_occupied_min = params["hvac"].get("occupied_target_temp_min", DEFAULT_TARGET_TEMP_OCCUPIED_MIN)
        self.target_temp_occupied_max = params["hvac"].get("occupied_target_temp_max", DEFAULT_TARGET_TEMP_OCCUPIED_MAX)
        self.target_temp_unoccupied_min = params["hvac"].get("unoccupied_target_temp_min", DEFAULT_TARGET_TEMP_UNOCCUPIED_MIN)
        self.target_temp_unoccupied_max = params["hvac"].get("unoccupied_target_temp_max", DEFAULT_TARGET_TEMP_UNOCCUPIED_MAX)
        self.kwh_per_degree_day = params["hvac"].get("kWh_per_degree_day", DEFAULT_KWH_PER_DEGREE_DAY)
        self.degrees_change_per_s = params["hvac"].get("degrees_change_per_hour", DEFAULT_DEGREES_CHANGE_PER_HOUR) / (60*60.0)
        self.hvac_reliability = params["hvac"].get("hvac_reliability", DEFAULT_RELIABILITY)
        self.set_property("device_type", "HVAC")
        self.set_property("mode", "fan")
        self.set_property("pump_run", False)
        self.set_property("boiler_selection_mode", random.randrange(1,3))   # A number 0..3 expressing which of two boilers is supposed to be running
        self.pump_run_on_start_time = self.engine.get_now()
        self.temperature = 20
        self.hvac_functional = True # If false then we won't respond to demand
        self.engine.register_event_in(POLL_INTERVAL_S, self.tick_temperature, self, self)

    def comms_ok(self):
        return super(Hvac,self).comms_ok()

    def external_event(self, event_name, arg):
        super(Hvac,self).external_event(event_name, arg)
        pass

    def close(self):
        super(Hvac,self).close()

    # Private methods
    def get_sun(self):  # Theoretical strength of the sun (if no clouds)
        lon,lat = self.properties.get("longitude"), self.properties.get("latitude")
        return solar.sun_bright(self.engine.get_now(), lon, lat)

    def external_temp_and_insolation(self):
        """Get these from this device, if the behaviours exist on this device, else from another device at the same level of the model"""
        external_temperature = 12
        cloud_cover = 0.5
        found_weather = False
        if self.property_exists("external_temperature"):        # Weather sensors exists on this device
            external_temperature = self.get_property("external_temperature")
            cloud_cover = self.get_property("cloud_cover")
            found_weather = True
        else:
            for peer in self.model.get_peers_and_below(self):   # Look for weather sensor at same level in hierarchy
                if peer.get_property_or_None("device_type") == "weather":
                    found_weather = True
                    external_temperature = peer.get_property("external_temperature")
                    cloud_cover = peer.get_property("cloud_cover")

        if not found_weather:
            logging.warning("No weather sensor found in same device or same level of model as HVAC device "+str(self.get_property("$id")))

        sun = self.get_sun()
        insolation = sun * cloud_cover

        return external_temperature, insolation

    def get_target_temp_min_max(self):
        open = opening_times.chance_of_occupied(self.engine.get_now(), self.opening_times) != 0
        if open:
            return self.target_temp_occupied_min, self.target_temp_occupied_max
        else:
            return self.target_temp_unoccupied_min, self.target_temp_unoccupied_max

    def indoor_outdoor_coupling(self):
        if self.property_exists("window"):
            if self.get_property("window")=="open":
                return INDOOR_OUTDOOR_COUPLING_WINDOW_OPEN
        return INDOOR_OUTDOOR_COUPLING

    def tick_temperature(self, _):
        self.hvac_functional = random.random() <= self.hvac_reliability
        old_mode = self.get_property("mode")
        # Drive internal temperature according to weather
        external_temp, insolation = self.external_temp_and_insolation()
        self.set_property("insolation", insolation)
        effective_ext_temp = external_temp + insolation * INSOLATION_FORCING_DEGREES
        coupling = self.indoor_outdoor_coupling()
        self.temperature = self.temperature * (1.0 - coupling) + effective_ext_temp * coupling
        # Drive internal temperature according to HVAC
        target_temp_min, target_temp_max = self.get_target_temp_min_max()
        if self.temperature < target_temp_min :
            desired_mode = "heat"
        elif self.temperature > target_temp_max :
            desired_mode = "cool"
        else:
            desired_mode = "fan"

        if self.hvac_functional:
            mode = desired_mode
        else:
            if desired_mode != "fan":
                logging.info("HVAC " + str(self.get_property("$id")) + " currently not functional, so ignored call for " + desired_mode)
            mode = "fan"

        if mode == "heat":
            delta = min(target_temp_min + TEMP_HYSTERESIS - self.temperature, self.degrees_change_per_s * POLL_INTERVAL_S) # Go as fast as you can, but don't shoot beyond the ideal temperature
            self.temperature += delta
            kW = self.kwh_per_degree_day * delta * (float(POLL_INTERVAL_S) / DAYS)
        elif mode == "cool":
            delta = min(self.temperature - TEMP_HYSTERESIS - target_temp_max, self.degrees_change_per_s * POLL_INTERVAL_S)
            self.temperature -= delta
            kW = self.kwh_per_degree_day * delta * (float(POLL_INTERVAL_S) / DAYS)  # For now assume cooling costs same as heating
        else:   # Fan
            kW = 0

        p = {   "kW" : kW,
                "temperature" : int(self.temperature*10)/10.0,
                "external_temperature" : external_temp,
                "target_temp_ideal" : self.target_temp_ideal,
                "target_temp_min" : target_temp_min,
                "target_temp_max" : target_temp_max
                }
        if old_mode != mode:
            p.update( { "mode" : mode } )   # Only send if it's changed
        self.set_properties(p)

        pump_run = self.get_property("pump_run")
        if (old_mode != "fan") and (mode=="fan"):   # Start pump run-on
            self.pump_run_on_start_time = self.engine.get_now()
        if (mode=="fan") and pump_run:   # Finish pump run-on
            if self.engine.get_now() - self.pump_run_on_start_time > PUMP_RUN_ON_S:
                pump_run = False
        else:
            pump_run = True
        if self.get_property("pump_run") != pump_run:
            self.set_property("pump_run", pump_run)

        p = {
                "boiler1_run" : (mode=="heat") and (((self.get_property("boiler_selection_mode") & 1) != 0) or random.random() < 0.05),  # Small chance of boilers running when the Mode says they shouldn't
                "boiler2_run" : (mode=="heat") and (((self.get_property("boiler_selection_mode") & 2) != 0) or random.random() < 0.05)
        }
        if(random.random() < 0.01):
            p.update({"boiler_selection_mode" : random.randrange(1,3)})    # Always have SOME boiler on
        self.set_properties(p)

        self.engine.register_event_in(POLL_INTERVAL_S, self.tick_temperature, self, self)

