#!/usr/bin/env python
#
# SIM
# Simulate events in (non-)real-time
#
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

import logging
import threading
import time

from synth.device.simulation.helpers import ISO8601

simTime = 0  # Global "now" in epoch-seconds
startTime = None
endTime = None
events = []  # A sorted list of simulation callbacks: [(epochTime,function,arg), ...]

caughtUp = False


def caught_up_callback_fn():
    pass  # Called when simulator catches-up with real-time

caught_up_callback = caught_up_callback_fn

# Protects events[] and simTime to make sim thread-safe, as event-injection can
# happen asynchronously (we can't use Queues because we need peeking)
simLock = threading.Lock()


# Set up Python logger to report simulated time
def in_simulated_time():
    return ISO8601.epoch_seconds_to_datetime(
        # Logging might be emitted within sections where simLock is acquired, so we accept
        # a small chance of duff time values in log messages, in order to allow diagnostics without deadlock
        get_time_no_lock()).timetuple()


def init_logging():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S'
                        )
    logging.Formatter.converter = in_simulated_time  # Make logger use simulated time


init_logging()


# UTILITY FUNCTIONS (no side effects)

def minutes(n):
    return n * 60


def hours(n):
    return minutes(n) * 60


def days(n):
    return hours(n) * 24


def weeks(n):
    return days(n) * 7


def months(n):
    return days(n) * 30


def years(n):
    return days(n) * 365


def init(cb):
    global caught_up_callback
    caught_up_callback = cb


# Simulation control and monitoring
# All times in epoch-seconds

def set_time(epoch_secs):
    global simTime
    simLock.acquire()
    simTime = epoch_secs
    simLock.release()


def set_time_str(time_string, is_start_time=False):
    global startTime, simTime
    if time_string == "now":
        set_time(time.time())
    elif time_string.startswith("-"):  # A day in the past specified with "-N", e.g. "-180"
        set_time(time.time() + int(time_string) * 60 * 60 * 24)
    else:
        set_time(ISO8601.to_epoch_seconds(time_string))
    if is_start_time:
        startTime = simTime


def set_end_time_str(time_string):
    global endTime
    if time_string in [None, "now"]:
        endTime = time_string
    else:
        endTime = ISO8601.to_epoch_seconds(time_string)


def get_time():
    global simTime
    simLock.acquire()
    t = simTime
    simLock.release()
    return t


def get_time_no_lock():
    global simTime
    return simTime


def get_time_1000():
    return int(get_time() * 1000)


def get_time_str():
    return str(ISO8601.epoch_seconds_to_iso8601(get_time()))


def events_to_come():
    global caughtUp
    simLock.acquire()  # <--
    try:
        if endTime is None:
            if len(events) > 0:
                if events[0][0] >= time.time():
                    if not caughtUp:
                        logging.info("Caught-up with real time")
                        caught_up_callback()  # Mustn't create new events, or deadlock will occur
                    caughtUp = True
            return True
        if endTime == "now":  # Terminate when we've caught-up with real-time
            if len(events) < 1:
                logging.info("No more events")
                return False
            if events[0][0] >= time.time():
                logging.info("Caught-up with real time")
                return False
            return True
        if events[0][0] > endTime:
            logging.info("Reached simulation end time")
            return False
        return True
    finally:
        simLock.release()  # -->


def next_event():
    # If we have to wait for real time to catch up, then
    # new external events can appear asychronously whilst we wait.
    # So we wait only a short period and then release so can reassess from scratch again soon
    # (and so any other heartbeats can happen)
    global events
    simLock.acquire()  # <---
    if len(events) < 1:
        logging.info("No events pending")
        wait = 1.0
    else:
        (t, fn, arg) = events[0]
        wait = t - time.time()
        if wait <= 0:
            events.pop(0)
            simLock.release()  # --->
            set_time(t)
            logging.debug(str(fn.__name__) + "(" + str(arg) + ")")
            fn(arg)  # Note that this is likely to itself inject more events, so we must have released lock
            return
    simLock.release()  # --->
    logging.info("Waiting " + str(wait) + "s for real time")
    time.sleep(min(1.0, wait))
    set_time(time.time())  # So that any events injected asynchronously will correctly get stamped with current time


def inject_events(times, func, arg=None):
    global events
    l = [(t, func, arg) for t in times]
    simLock.acquire()
    events = sorted(events + l)
    simLock.release()


def inject_event(_time, func, arg=None):
    global events
    l = [(_time, func, arg)]
    simLock.acquire()
    events = sorted(events + l)
    simLock.release()


def inject_event_delta(delta_time, func, arg=None):
    global events
    l = [(get_time() + delta_time, func, arg)]
    simLock.acquire()
    events = sorted(events + l)
    simLock.release()
