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

import time
import logging
import ISO8601
import threading

simTime = 0     # Global "now" in epoch-seconds
startTime = None
endTime = None
events = []     # A sorted list of simulation callbacks: [(epochTime,function,arg), ...]

caughtUp = False
caughtUpCallback = None # Called when simulator catches-up with real-time

simLock = threading.Lock() # Protects events[] and simTime to make sim thread-safe, as event-injection can happen asynchronously (we can't use Queues because we need peeking)

# Set up Python logger to report simulated time
def inSimulatedTime(self,secs=None):
    return ISO8601.epochSecondsToDatetime(getTimeNoLock()).timetuple()  # Logging might be emitted within sections where simLock is acquired, so we accept a small chance of duff time values in log messages, in order to allow diagnostics without deadlock

def initLogging():
    logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%dT%H:%M:%S'
                    )
    logging.Formatter.converter=inSimulatedTime # Make logger use simulated time

initLogging()

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
    global caughtUpCallback
    caughtUpCallback = cb

### Simulation control and monitoring
### All times in epoch-seconds

def setTime(epochSecs):
    global simTime
    simLock.acquire()
    simTime = epochSecs
    simLock.release()

def setTimeStr(timeString, isStartTime=False):
    global startTime, simTime
    if timeString=="now":
        setTime(time.time())
    elif timeString.startswith("-"):    # A day in the past specified with "-N", e.g. "-180"
        setTime(time.time()+int(timeString)*60*60*24)
    else:
        setTime(ISO8601.toEpochSeconds(timeString))
    if isStartTime:
        startTime = simTime

def setEndTimeStr(timeString):
    global endTime
    if timeString in[None,"now"]:
        endTime = timeString
    else:
        endTime = ISO8601.toEpochSeconds(timeString)

def getTime():
    global simTime
    simLock.acquire()
    t = simTime
    simLock.release()
    return t

def getTimeNoLock():
    global simTime
    return simTime

def getTime1000():
    return int(getTime() * 1000)

def getTimeStr():
    return str(ISO8601.epochSecondsToISO8601(getTime()))

def eventsToCome():
    global caughtUp
    simLock.acquire()       # <--
    try:
        if endTime==None:
            if len(events) > 0:
                if events[0][0] >= time.time():
                    if not caughtUp:
                        logging.info("Caught-up with real time")
                        caughtUpCallback()  # Mustn't create new events, or deadlock will occur
                    caughtUp = True
            return True
        if endTime=="now":    # Terminate when we've caught-up with real-time
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
        simLock.release()   # -->
        
def nextEvent():
    # If we have to wait for real time to catch up, then
    # new external events can appear asychronously whilst we wait.
    # So we wait only a short period and then release so can reassess from scratch again soon (and so any other heartbeats can happen)
    global events
    simLock.acquire()           # <---
    if len(events) < 1:
        logging.info("No events pending")
        wait = 1.0
    else:
        (t,fn,arg) = events[0]
        wait = t - time.time()
        if wait <= 0:
            events.pop(0)
            simLock.release()   # --->
            setTime(t)
            logging.debug(str(fn.__name__)+"("+str(arg)+")")
            fn(arg)             # Note that this is likely to itself inject more events, so we must have released lock
            return
    simLock.release()           # --->
    logging.info("Waiting "+str(wait)+"s for real time")
    time.sleep(min(1.0, wait))
    setTime(time.time())    # So that any events injected asynchronously will correctly get stamped with current time

def injectEvents(times, func, arg=None):
    global events
    L = [(t,func,arg) for t in times]
    simLock.acquire()
    events = sorted(events + L)
    simLock.release()

def injectEvent(time, func, arg=None):
    global events
    L = [(time, func, arg)]
    simLock.acquire()
    events = sorted(events + L)
    simLock.release()
    
def injectEventDelta(deltaTime, func, arg=None):
    global events
    L = [(getTime() + deltaTime, func, arg)]
    simLock.acquire()
    events = sorted(events + L)
    simLock.release()
    
