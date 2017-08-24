"""EXPECT
   Plug-in device function which watches-out for expected incoming messages.
   We're given a time function (i.e. one which returns 0 or 1 at different moments in time)
   and an event name. Our "window" when we expect to receive exactly one event
   is each period where the function returns 1.
   We expect to receive no events when it is returning 0.

   NOTE: Unlike most other moduels in this package, this module distinguishes
   "real time" from "sim time" because it deals with live, incoming, asynchronous events.
   Reason: Even if the general simulator has caught-up with real-time,
   simulation time only advances event-to-event. So if there are no events scheduled
   for the next 100 seconds then "engine.get_now()" will return a time 100 seconds
   into the future, and the simulator just waits doing nothing until real time
   catches-up with that. But this module can receive events during that time,
   and wants to time-stamp them correctly and perhaps schedule other events for immediate execution.
   So for that it needs to use real time not sim time.

   This isn't an issue for events coming from the simulator (e.g. ticks) because they should fire
   at almost exactly the right real-time.
"""

from device import Device
import pendulum
import logging
import time
from common import importer

# Types of event that we log
EVENT_IN_WINDOW = 'E'           # As expected we got an event within the window
EVENT_OUTSIDE_WINDOW = 'O'      # We got an event unexpectedly outside the window
MISSING_EVENT = 'X'             # We failed to get any event within the window
DUPLICATE_EVENT_IN_WINDOW = 'D' # We got a duplicate event within the window

def live_time(engine):
    """See NOTE in Module docs"""
    return min(time.time(), engine.get_now()) # Has no effect for historical simulations, but ensures that real-time simualations record and schedule correctly

class Expect(Device):
    def __init__(self, time, engine, update_callback, params):
        super(Expect,self).__init__(time, engine, update_callback, params)
        fn_name = params["expect"]["timefunction"].keys()[0]
        fn_class = importer.get_class("timefunction", fn_name)
        self.expected_timefunction = fn_class(engine, params["expect"]["timefunction"])
        self.expected_event_name = params["expect"]["event_name"]
        self.event_log = []  # List of (event_time, event_type)
        self.seen_event_in_this_window = False

        t_next = self.expected_timefunction.next_change(live_time(engine))
        if self.expected_timefunction.state(live_time(engine)):
            self.engine.register_event_at(t_next, self.tick_window_end, self)
        else:
            self.engine.register_event_at(t_next, self.tick_window_start, self)

    def comms_ok(self):
        return super(Expect,self).comms_ok()

    def external_event(self, event_name, arg):
        logging.info("Expect.py 1 saw event "+event_name+" on device "+self.properties["$id"])
        super(Expect,self).external_event(event_name, arg)
        logging.info("Expect.py 2 saw event "+event_name+" on device "+self.properties["$id"])
        if event_name==self.expected_event_name:
            logging.info("Expect.py acting on event "+event_name+" on device "+self.properties["$id"])
            t = live_time(self.engine)
            if self.expected_timefunction.state(t):
                if self.seen_event_in_this_window:
                    self.add_event(t,DUPLICATE_EVENT_IN_WINDOW)
                else:
                    self.add_event(t,EVENT_IN_WINDOW)
                    self.seen_event_in_this_window = True
            else:
                self.add_event(t,EVENT_OUTSIDE_WINDOW)
        else:
            logging.info("Doesn't match expected event name "+str(self.expected_event_name))

    # Private methods
    
    def tick_window_start(self,_):
        self.seen_event_in_this_window = False
        self.engine.register_event_at(self.expected_timefunction.next_change(), self.tick_window_end, self)

    def tick_window_end(self,_):
        self.engine.register_event_at(self.expected_timefunction.next_change(), self.tick_window_start, self)
        if not self.seen_event_in_this_window:
            self.add_event(self.engine.get_now(),MISSING_EVENT)

    def add_event(self, t, event):
        self.event_log.append( (t, event) )
        self.dump_events()
        
    def dump_events(self):
        print "Log of (un)expected events:"
        for L in self.event_log:
            print pendulum.from_timestamp(L[0]).to_datetime_string() + " " + str(L[1])

