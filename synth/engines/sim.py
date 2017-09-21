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
import threading
import bisect
from common import ISO8601
from common.conftime import richTime

from engines.engine import Engine

simLock = threading.Lock() # Protects events[] and simTime to make sim thread-safe, as event-injection can happen asynchronously (we can't use Queues because we need peeking)
# TODO: Get rid of this global

class Sim(Engine):
    """Capable of both historical and real-time simulation,
       and of moving smoothly between the two"""

    def __init__(self, params, cb = None, event_count_callback = None):
        self.set_start_time_str(params.get("start_time", "now"))
        self.set_end_time_str(params.get("end_time", None))
        self.end_after_events = params.get("end_after_events", None)
        self.caughtUpCallback = cb
        self.caughtUp = False
        self.event_count_callback = event_count_callback
        self.events = []     # A sorted list of simulation callbacks: [(epochTime,function,arg), ...]

    def set_now(self,epochSecs):
        simLock.acquire()
        self.simTime = epochSecs
        simLock.release()

    def set_now_str(self,timeString):
        self.set_time(richTime(timeString))

    def set_start_time_str(self, timeString):
        t = richTime(timeString)
        self.startTime = t
        self.set_now(t)

    def set_end_time_str(self,timeString):
        """<timeString> can be:
            None (for never end)
            'now' to end when simulation reaches current time
            'when_done' to end when no further events are pending
            or else an ISO8601 absolute or relative time"""
        if timeString in [None, "now", "when_done"]:
            self.endTime = timeString
        else:
            self.endTime = richTime(timeString)

    def get_start_time(self):
        return self.startTime
    
    def get_now(self):
        simLock.acquire()
        t = self.simTime
        simLock.release()
        return t

    def get_now_no_lock(self):
        return self.simTime

    def get_now_1000(self):
        return int(self.get_now() * 1000)

    def get_now_str(self):
        return str(ISO8601.epoch_seconds_to_ISO8601(self.get_now()))

    def events_to_come(self):
        """Return False if simulation has definitely ended"""
        def caughtUp():
            if not self.caughtUp:
                logging.info("Caught-up with real time")
                if self.caughtUpCallback:
                    self.caughtUpCallback()  # Mustn't create new events, or deadlock will occur
            self.caughtUp = True

        if self.end_after_events:
            if self.event_count_callback() >= self.end_after_events:
                logging.info("Reached target of "+str(self.end_after_events)+" events")
                return False
            
        try:
            simLock.acquire()       # <--
            
            if self.simTime >= time.time() - 1.0:   # Allow a bit of slack because otherwise we might never quite catch-up, because we always wait to ensure we don't
                caughtUp()

            if self.endTime == None:
                return True

            if self.endTime == "when_done":
                keep_going = len(self.events)>0
                if not keep_going:
                    logging.info("No further events")
                return keep_going
                           
            if self.endTime=="now":    # Terminate when we've caught-up with real-time
                if self.simTime >= (time.time()-1.0):   # Allow some slack
                    caughtUp()
                    logging.info("Caught up with real time")
                    return False
                return True

            if self.simTime >= self.endTime:
                logging.info("Reached simulation end time")
                return False
            return True
        finally:
            simLock.release()   # -->
            
    def next_event(self):
        """Execute next event

           If we have to wait for real time to catch up, then
           new external events can appear asychronously whilst we wait.
           So we wait only a short period and then release so can reassess from scratch again soon (and so any other heartbeats can happen)."""
        simLock.acquire()           # <---
        if len(self.events) < 1:
            logging.info("No events pending")
            wait = 1.0
        else:
            (t,fn,arg) = self.events[0]
            wait = t - time.time()
            if wait <= 0:
                self.events.pop(0)
                simLock.release()   # --->
                self.set_now(t)
                logging.debug(str(fn.__name__)+"("+str(arg)+")")
                fn(arg)             # Note that this is likely to itself inject more events, so we must have released lock
                return
        simLock.release()           # --->
        logging.info("Waiting {:.2f}s for real time".format(wait))
        time.sleep(min(1.0, wait))
        self.set_now(time.time())    # So that any events injected asynchronously will correctly get stamped with current time

    def _add_event(self, time, func, arg):
        if time == 0:
            logging.info("Advisory: Setting event at epoch=0 (not illegal, but often a sign of a mistake)")
        elif time < self.get_now():
            logging.info("Advisory: Setting event in the past (not illegal, but often a sign of a mistake)")

        simLock.acquire()
        bisect.insort(self.events, (time, func, arg)) # Efficient since we know the list is kept sorted
        simLock.release()

##        try:
##            simLock.acquire()   # <---
##            if len(self.events) > 0:    # Avoid sorting whole list if we're just adding to end. But this never happens!
##                if self.events[-1] < L[0]:
##                    self.events.extend(L)
##                    return
##            self.events = sorted(self.events + L)   # TODO: Might be more efficient to append and then sort in place?
##        finally:
##            simLock.release()   # --->

          
    def register_event_at(self, time, func, arg=None):
        self._add_event(time, func, arg)
        
    def register_event_in(self, deltaTime, func, arg=None):
        assert deltaTime >= 0
        self._add_event(self.get_now() + deltaTime, func, arg)

