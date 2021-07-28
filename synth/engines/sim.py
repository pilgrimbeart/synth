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
import queue
from common import ISO8601
from common.conftime import richTime

from engines.engine import Engine

class Sim(Engine):
    """Capable of both historical and real-time simulation,
       and of moving smoothly between the two"""

    def __init__(self, params, cb = None, event_count_callback = None):
        self.sim_lock = threading.Lock() # Protects sim_time to make sim thread-safe, as event-injection can happen asynchronously
        self.set_start_time_str(params.get("start_time", "now"))
        self.set_end_time_str(params.get("end_time", None))
        self.end_after_events = params.get("end_after_events", None)
        self.caught_up_callback = cb
        self.caught_up = False
        self.event_count_callback = event_count_callback
        # self.events = []      # A sorted list of simulation callbacks: [(epochTime,sortkeycount,function,arg,device), ...]
        self.events = queue.PriorityQueue()
        self.sort_key_count = 0 # A secondary key which ensures that events with identical event times are sorted in order of their insertion
        self.next_event_time = None

    def set_now(self, epochSecs):
        self.sim_lock.acquire()
        self.sim_time = epochSecs
        self.sim_lock.release()

    def set_now_str(self,timeString):
        self.set_time(richTime(timeString)) # ??? doesn't seem to exist, is this function ever called?

    def set_start_time_str(self, timeString):
        t = richTime(timeString)
        self.start_time = t
        self.set_now(t)

    def set_end_time_str(self,timeString):
        """<timeString> can be:
            None (for never end)
            'now' to end when simulation reaches current time (i.e. current time when simulation was run - otherwise it gets hard to e.g. schedule events for end time!)
            'when_done' to end when no further events are pending
            or else an ISO8601 absolute or relative time"""
        if timeString in [None, "when_done"]:
            self.end_time = timeString
        elif timeString == "now":
            self.end_time = time.time()
        else:
            self.end_time = richTime(timeString)

    def get_start_time(self):
        return self.start_time

    def get_end_time(self):
        return self.end_time
    
    def get_now(self):
        self.sim_lock.acquire()
        t = self.sim_time
        self.sim_lock.release()
        return t

    def get_now_no_lock(self):
        return self.sim_time

    def get_now_1000(self):
        return int(self.get_now() * 1000)

    def get_now_str(self):
        return str(ISO8601.epoch_seconds_to_ISO8601(self.get_now()))

    def events_to_come(self):
        """Return False if simulation has definitely ended"""
        def caught_up():
            if not self.caught_up:
                logging.info("Caught-up with real time")
                if self.caught_up_callback:
                    self.caught_up_callback()  # Mustn't create new events, or deadlock will occur
            self.caught_up = True

        if self.end_after_events:
            if self.event_count_callback() >= self.end_after_events:
                logging.info("Reached target of "+str(self.end_after_events)+" events")
                return False
            
        try:
            self.sim_lock.acquire()       # <--
            
            if self.sim_time >= time.time() - 1.0:   # Allow a bit of slack because otherwise we might never quite catch-up, because we always wait to ensure we don't
                caught_up()

            if self.end_time == None:
                return True

            if self.end_time == "when_done":
                keep_going = not self.events.empty()
                if not keep_going:
                    logging.info("No further events")
                return keep_going
                           
            if self.end_time=="now":    # Terminate when we've caught-up with real-time
                if self.sim_time >= (time.time()-1.0):   # Allow some slack
                    caught_up()
                    logging.info("Caught up with real time")
                    return False
                return True

            if self.sim_time >= self.end_time:
                logging.info("Reached simulation end time with "+str(self.events.qsize())+" events still in future")
                return False
            return True
        finally:
            self.sim_lock.release()   # -->
            
    def next_event(self):
        """Execute next event

           If we have to wait for real time to catch up, then
           new external events can appear asychronously whilst we wait.
           So we wait only a short period and then release so can reassess from scratch again soon (and so any other heartbeats can happen)."""
        self.sim_lock.acquire()           # <---
        if self.events.qsize() < 1:
            logging.info("No events pending")
            wait = 1.0
        else:
            (t,skc,fn,arg,dev) = self.events.get_nowait()   # Get earliest event. Raises exception if queue empty.
            wait = t - time.time()
            if wait <= 0:
                self.sim_lock.release()   # --->
                self.set_now(t)
                logging.debug(str(fn.__name__)+"("+str(arg)+")")
                fn(arg)             # Note that this is likely to itself inject more events, so we must have released lock
                return
            self.events.put_nowait((t,skc,fn,arg,dev))  # Push unused event back on the queue
        self.sim_lock.release()           # --->
        if t != self.next_event_time:
            if wait >= 1.0:
                logging.info("Waiting {:.2f}s for real time".format(wait))
            self.next_event_time = t
        time.sleep(min(1.0, wait))
        self.set_now(time.time())    # So that any events injected asynchronously will correctly get stamped with current time

    def _add_event(self, time, func, arg, dev):
        """If multiple events are inserted at the same time, we guarantee they'll get executed in insertion order.
        We do this by ensuring that the second item in the tuple is a monotonically rising number"""
        if time == 0:
            logging.info("Advisory: Setting event at epoch=0 (not illegal, but often a sign of a mistake)")
        elif time < self.get_now():
            logging.info("Advisory: Setting event in the past (not illegal, but often a sign of a mistake)")

        self.sim_lock.acquire() # Not strictly needed, as our priority queue has its own thread lock
        self.events.put_nowait((time, self.sort_key_count, func, arg, dev))
        self.sort_key_count += 1
        self.sim_lock.release()

##        try:
##            self.sim_lock.acquire()   # <---
##            if len(self.events) > 0:    # Avoid sorting whole list if we're just adding to end. But this never happens!
##                if self.events[-1] < L[0]:
##                    self.events.extend(L)
##                    return
##            self.events = sorted(self.events + L)   # TODO: Might be more efficient to append and then sort in place?
##        finally:
##            self.sim_Lock.release()   # --->

    def remove_all_events_for_device(self, dev):
        assert(False)   ## TODO: Implement!
        self.sim_lock.acquire()
        old_len = len(self.events)
        self.events = [e for e in self.events if e[4] != dev] # Remove any events with device=dev
        new_len = len(self.events)
        self.sim_lock.release()
        logging.info("Removed all events for device "+str(dev)+ " (" + str(old_len-new_len)+" events removed)")
          
    def register_event_at(self, time, func, arg, device):
        self._add_event(time, func, arg, device)
        
    def register_event_in(self, deltaTime, func, arg, device):
        assert deltaTime >= 0
        self._add_event(self.get_now() + deltaTime, func, arg, device)

