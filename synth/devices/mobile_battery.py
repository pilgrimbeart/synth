#!/usr/bin/env python

# Copyright (c) 2017 DevicePilot Ltd.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import logging
import math
import random
import traceback

import synth.devices.simulation.helpers.timewave
from synth.devices.simulation import sim

from synth.simulation.solar import solar_math

devices = []


def update_callback_fn(_):
    pass


update_callback = update_callback_fn

logfile = None
DEFAULT_BATTERY_LIFE_S = sim.minutes(5)  # For interactive process demo

GOOD_RSSI = -50.0
BAD_RSSI = -120.0


def init(updatecallback, logfile_name):
    global update_callback
    global logfile
    update_callback = updatecallback
    logfile = open("../synth_logs/" + logfile_name + ".evt", "at", 0)  # Unbuffered
    logfile.write("*** New simulation starting at real time " + datetime.datetime.now().ctime() + "\n")


def num_devices():
    global devices
    n = len(devices)
    return n


def log_entry(properties):
    logfile.write(sim.get_time_str() + " ")
    for k in sorted(properties.keys()):
        s = str(k) + ","
        # noinspection PyTypeChecker
        if isinstance(properties[k], basestring):
            try:
                s += properties[k].encode('ascii',
                                          'ignore')  # Python 2.x barfs if you try to write unicode into an ascii file
            except UnicodeError:
                s += "<unicode encoding error>"
        else:
            s += str(properties[k])
        s += ","
        logfile.write(s)  # Property might contain unicode
    logfile.write("\n")


def log_string(s):
    logging.info(s)
    logfile.write(synth.simulation.sim.get_time_str() + " " + s + "\n")


def flush():
    logfile.close()


def external_event(params):
    # Accept events from outside world
    # (these have already been synchronised via the event queue so we don't need to worry about thread-safety here)
    global devices
    body = params["body"]
    try:
        logging.info("external Event received: " + str(params))
        for d in devices:
            if d.properties["$id"] == body["deviceId"]:
                arg = None
                if "arg" in body:
                    arg = body["arg"]
                d.external_event(body["eventName"], arg)
                return
        e = "No such devices"  # + str(deviceID) + " for incoming event " + str(eventName)
        log_string(e)
    except Exception as e:
        log_string("Error processing external event")
        logging.error("Error processing externalEvent: " + str(e))
        logging.error(traceback.format_exc())


class Device:
    def __init__(self, props):
        global devices
        self.properties = props
        devices.append(self)
        self.commsReliability = 1.0  # Either a fraction, or a string containing a specification of the trajectory
        self.commsUpDownPeriod = synth.simulation.sim.days(1)
        self.batteryLife = DEFAULT_BATTERY_LIFE_S
        self.batteryAutoreplace = False
        self.commsOK = True
        self.do_comms(self.properties)
        self.start_ticks()

    def start_ticks(self):
        synth.simulation.sim.inject_event_delta(self.batteryLife / 100.0, self.tick_battery_decay, self)
        synth.simulation.sim.inject_event_delta(synth.simulation.sim.hours(1), self.tick_hourly, self)
        synth.simulation.sim.inject_event_delta(0, self.tick_product_usage, self)  # Immediately

    def external_event(self, event_name, arg):
        s = "Processing external event " + event_name + " for devices " + str(self.properties["$id"])
        log_string(s)
        if event_name == "replaceBattery":
            self.set_property("battery", 100)
            self.start_ticks()

        # All other commands require devices to be functional!
        if self.get_property("battery") <= 0:
            log_string("...ignored because battery flat")
            return
        if not self.commsOK:
            log_string("...ignored because comms down")
            return

        if event_name == "upgradeFirmware":
            self.set_property("firmware", arg)
        if event_name == "factoryReset":
            self.set_property("firmware", self.get_property("factoryFirmware"))

    def tick_product_usage(self, _):
        if self.get_property("battery") > 0:
            self.set_property("buttonPress", 1)
            t = synth.simulation.helpers.timewave.next_usage_time(synth.simulation.sim.get_time(),
                                                                  ["Mon", "Tue", "Wed", "Thu", "Fri"],
                                                                         "06:00-09:00")
            synth.simulation.sim.inject_event(t, self.tick_product_usage, self)

    def set_comms_reliability(self, up_down_period=synth.simulation.sim.days(1), reliability=1.0):
        self.commsUpDownPeriod = up_down_period
        self.commsReliability = reliability
        synth.simulation.sim.inject_event_delta(0, self.tick_comms_up_down, self)  # Immediately

    def set_battery_life(self, mu, sigma, autoreplace=False):
        # Set battery life with a normal distribution which won't exceed 2 standard deviations
        life = random.normalvariate(mu, sigma)
        life = min(life, mu + 2 * sigma)
        life = max(life, mu - 2 * sigma)
        self.batteryLife = life
        self.batteryAutoreplace = autoreplace

    def tick_comms_up_down(self, _):
        if isinstance(self.commsReliability, (int, float)):  # Simple probability
            self.commsOK = self.commsReliability > random.random()
        else:  # Probability spec, i.e. varies with time
            rel_time = synth.simulation.sim.get_time() - synth.simulation.sim.startTime
            prob = synth.simulation.helpers.timewave.interp(self.commsReliability, rel_time)
            if self.property_exists("rssi"):  # Now affect comms according to RSSI
                rssi = self.get_property("rssi")
                radio_goodness = 1.0 - (rssi - GOOD_RSSI) / (BAD_RSSI - GOOD_RSSI)  # Map to 0..1
                radio_goodness = 1.0 - math.pow((1.0 - radio_goodness), 4)  # Skew heavily towards "good"
                prob *= radio_goodness
            self.commsOK = prob > random.random()

        delta_time = random.expovariate(1 / self.commsUpDownPeriod)
        delta_time = min(delta_time, self.commsUpDownPeriod * 100)  # Limit long tail
        synth.simulation.sim.inject_event_delta(delta_time, self.tick_comms_up_down, self)

    def do_comms(self, properties):
        if self.commsOK:
            update_callback(properties)
            log_entry(properties)

    def get_property(self, prop_name):
        return self.properties[prop_name]

    def property_exists(self, prop_name):
        return prop_name in self.properties

    def set_property(self, prop_name, value):
        new_props = {prop_name: value, "$ts": synth.simulation.sim.get_time_1000(),
                     "$id": self.properties["$id"]}
        self.properties.update(new_props)
        self.do_comms(new_props)

    def set_properties(self, new_props):
        self.properties.update(new_props)
        self.properties.update({"$ts": synth.simulation.sim.get_time_1000(), "$id": self.properties["$id"]})
        self.do_comms(new_props)

    def tick_battery_decay(self, _):
        v = self.get_property("battery")
        if v > 0:
            self.set_property("battery", v - 1)
            synth.simulation.sim.inject_event_delta(self.batteryLife / 100.0, self.tick_battery_decay, self)
        else:
            if self.batteryAutoreplace:
                logging.info("Auto-replacing battery")
                self.set_property("battery", 100)
                synth.simulation.sim.inject_event_delta(self.batteryLife / 100.0, self.tick_battery_decay, self)

    def tick_hourly(self, _):
        if self.get_property("battery") > 0:
            self.set_property("light", solar_math.sun_bright(synth.simulation.sim.get_time(),
                                                             (float(Device.get_property(self, "longitude")),
                                                              float(Device.get_property(self, "latitude")))
                                                             ))
            synth.simulation.sim.inject_event_delta(synth.simulation.sim.hours(1), self.tick_hourly, self)

# Model for comms unreliability
# -----------------------------
# Two variables define comms (un)reliability:
# a) up/down period: (secs) The typical period over which comms might change between working and failed state.
#    We use an exponential distribution with this value as the mean.
# b) reliability: (0..1) The chance of comms working at any moment in time
# The comms state is then driven independently of other actions.
# 
# Chance of comms failing at any moment is [0..1]
# Python function random.expovariate(lambda) returns values from 0 to infinity, with most common values in a hump in
# the middle such that that mean value is 1.0/<lambda>
