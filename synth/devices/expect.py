"""EXPECT
   Plug-in device function which watches-out for expected incoming messages.
   We're given a time function (i.e. one which returns 0 or 1 at different moments in time)
   and an event name. Our "window" when we expect to receive exactly one event
   is each period where the function returns 1.
   We expect to receive no events when it is returning 0.
"""

from device import Device
import pendulum
import logging
from common import importer

# Types of event that we log
EVENT_IN_WINDOW = 'EXPECTED_EVENT'              # As expected we got an event within the window
EVENT_OUTSIDE_WINDOW = 'OUTSIDE_WINDOW'         # We got an event unexpectedly outside the window
MISSING_EVENT = 'MISSING_EVENT'                 # We failed to get any event within the window
DUPLICATE_EVENT_IN_WINDOW = 'DUPLICATE_EVENT'   # We got a duplicate event within the window


class Expect(Device):
    """A device function which expects to receive events at certain times, and logs when it does/doesn't."""
    event_log = []  # List of (event_time, deviceID, event_type) - across all devices
    
    def __init__(self, time, engine, update_callback, params):
        super(Expect,self).__init__(time, engine, update_callback, params)
        fn_name = params["expect"]["timefunction"].keys()[0]
        fn_class = importer.get_class("timefunction", fn_name)
        self.expected_timefunction = fn_class(engine, params["expect"]["timefunction"])
        self.expected_event_name = params["expect"]["event_name"]
        self.seen_event_in_this_window = False

        t = engine.get_now()
        t_next = self.expected_timefunction.next_change(t)
        if self.expected_timefunction.state(t):
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
            t = self.engine.get_now()
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
        Expect.event_log.append( (t, self.properties["$id"], event) )
        self.dump_events()
        
    def dump_events(self):
        s = ""
        for L in Expect.event_log:
            s += pendulum.from_timestamp(L[0]).to_datetime_string() + "," + str(L[1]) + "," + str(L[2]) + "\n"
        logging.info("Log of (un)expected events:\n"+s)
