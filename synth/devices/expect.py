"""
expect
======
Watch-out for expected incoming messages.
A timefunction definition returns 0 or 1 at different moments in time.
We expect to receive no events when the timefunction returns 0.
We expect to receive exactly one event each time the timefunction returns 1.
Expect also creates a histogram chart of events, available on the webserver at /plots/<instancename>.html

Configurable parameters::

    {
        "timefunction" : defines window when events are expected
        "event_name" : name of expected incoming events
        "required_score_percent" : Optionally, raise an error if this minimum quality score isn't achieved by test end
    }

Device properties created::

    {
    }

"""

import logging, datetime
import pendulum
import requests, httplib, json
from device import Device
from common import importer
from common import plotting

# Types of event that we log
EVENT_IN_WINDOW = 'EXPECTED_EVENT'              # As expected we got an event within the window
DUPLICATE_EVENT_IN_WINDOW = 'DUPLICATE_EVENT'   # We got a duplicate event within the window
EVENT_OUTSIDE_WINDOW = 'OUTSIDE_WINDOW'         # We got an event unexpectedly outside the window
MISSING_EVENT = 'MISSING_EVENT'                 # We failed to get any event within the window

REPORT_PERIOD_S = 60
HISTO_BINS = 20

OUTPUT_DIRECTORY = "../synth_logs/"

class Expect(Device):
    """A device function which expects to receive events at certain times, and logs when it does/doesn't."""
    # Note below are all CLASS variables, not instance variables, because we only want one of them across all devices
    event_log = []  # List of (event_time, event_time_relative, event_time_modulo, deviceID, event_type) - across all devices
    score_log = []  # List of (time, score)
    initialised = False # Enables class to initialise things only once
 
    def __init__(self, instance_name, time, engine, update_callback, context, params):
        super(Expect,self).__init__(instance_name, time, engine, update_callback, context, params)
        tf = params["expect"]["timefunction"]
        self.expected_timefunction = importer.get_class("timefunction", tf.keys()[0])(engine, tf[tf.keys()[0]])
        self.expected_event_name = params["expect"]["event_name"]
        self.expected_instance_name = context["instance_name"]
        self.expected_required_score_percent = params["expect"].get("required_score_percent", None)
        if not Expect.initialised:
            self.engine.register_event_in(REPORT_PERIOD_S, self.tick_send_report, self)
            Expect.initialised = True

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
        super(Expect,self).external_event(event_name, arg)
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

    def close(self):
        super(Expect,self).close()
        if Expect.initialised:
            Expect.initialised = False
            if self.expected_required_score_percent is not None:
                actual_score_percent = self.score() * 100
                logging.info("Expect required_score_percent=" + str(self.expected_required_score_percent) +
                             " actual_score_percent="+str(actual_score_percent))
                if actual_score_percent >= self.expected_required_score_percent:
                    logging.info("Expect score PASSED")
                else:
                    assert False, "Expect score FAILED"

    # Private methods
    
    def tick_window_start(self,_):
        self.seen_event_in_this_window = False
        self.engine.register_event_at(self.expected_timefunction.next_change(), self.tick_window_end, self)

    def tick_window_end(self,_):
        self.engine.register_event_at(self.expected_timefunction.next_change(), self.tick_window_start, self)
        if not self.seen_event_in_this_window:
            self.add_event(self.engine.get_now(),MISSING_EVENT)

    def add_event(self, t, event):
        rel_t = t - self.creation_time  # Convert to relative time
        Expect.event_log.append( (t, rel_t, self.modulo_fraction(rel_t), self.properties["$id"], event) )
        
    def score(self):
        """Return a quality score of between 0.0 and 1.0."""
        if len(Expect.event_log)==0:
            return 1.0
        sum = 0
        for L in Expect.event_log:
            if L[4]==EVENT_IN_WINDOW:
                sum += 1
        sum = sum / float(len(Expect.event_log))

        return sum

    def modulo_fraction(self, rel_time):
        """Wrap time (relative to start) around our window"""
        period = self.expected_timefunction.period()
        return (float(rel_time) % period) / period

    def create_histo(self):
        """Plot logged events as a set of histograms."""
        histo_in_window = [0] * HISTO_BINS
        histo_duplicate_event = [0] * HISTO_BINS
        histo_outside_window = [0] * HISTO_BINS
        histo_missing_event = [0] * HISTO_BINS
        for L in Expect.event_log:
            modulo_time = self.modulo_fraction(L[1]) # Normalise time to 0..1
            bin = int(HISTO_BINS * modulo_time)
            if L[4]==EVENT_IN_WINDOW:
                histo_in_window[bin] += 1
            elif L[4]==DUPLICATE_EVENT_IN_WINDOW:
                histo_duplicate_event[bin] += 1
            elif L[4]==EVENT_OUTSIDE_WINDOW:
                histo_outside_window[bin] += 1
            elif L[4]==MISSING_EVENT:
                histo_missing_event[bin] += 1
            else:
                assert False

        expected=[]
        period = self.expected_timefunction.period()
        for ti in range(HISTO_BINS):
            t = ti * float(period) / HISTO_BINS
            expected.append(self.expected_timefunction.state(t, t_relative=True))

        return (period, expected, [histo_in_window, histo_duplicate_event, histo_outside_window, histo_missing_event])

    def output_plot(self):
        histo = self.create_histo()
        (e,d,o,m) = (sum(histo[2][0]), sum(histo[2][1]), sum(histo[2][2]), sum(histo[2][3]))
        logging.info("Received events: Expected:"+str(e)+" Duplicate:"+str(d)+" Outside:"+str(o)+" Missing:"+str(m))
        logging.info("So E+D+O="+str(e+d+o)+" events received so far")
        div1 = plotting.plot_histo(histo[0], histo[1], histo[2])
        div2 = plotting.plot_score_log(Expect.score_log)
        plotting.write_page(self.instance_name, [div1, div2])

    def write_stats(self):
        f = open(OUTPUT_DIRECTORY+self.expected_instance_name+"_expected.csv","wt")
        f.write("Absolute time, elapsed time, modulo time, Device ID, Event type\n")
        for L in Expect.event_log:
            f.write(','.join(map(str, L))+"\n")
        f.close()
        
    def tick_send_report(self, _):
        Expect.score_log.append( (self.engine.get_now(), self.score() * 100) )

        self.output_plot()
        self.write_stats()
        self.engine.register_event_in(REPORT_PERIOD_S, self.tick_send_report, self)
        
