"""EXPECT
   Plug-in device function which watches-out for expected incoming messages.
   We're given a time function (i.e. one which returns 0 or 1 at different moments in time)
   and an event name. Our "window" when we expect to receive exactly one event
   is each period where the function returns 1.
   We expect to receive no events when it is returning 0.
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

REPORT_PERIOD_S = 1*60
HISTO_BINS = 20

class Expect(Device):
    """A device function which expects to receive events at certain times, and logs when it does/doesn't."""
    # Note below are all CLASS variables, not instance variables, because we only want one of them across all devices
    event_log = []  # List of (event_time_relative, deviceID, event_type) - across all devices
    score_log = []  # List of (time, score)
    slack_initialised = False
    
    def __init__(self, instance_name, time, engine, update_callback, params):
        super(Expect,self).__init__(instance_name, time, engine, update_callback, params)
        tf = params["expect"]["timefunction"]
        self.expected_timefunction = importer.get_class("timefunction", tf.keys()[0])(engine, tf[tf.keys()[0]])
        self.expected_event_name = params["expect"]["event_name"]

        self.slack_webhook = params["expect"].get("slack_webhook", None)
        if not Expect.slack_initialised:    # Only do this for first device registered
            self.post_to_slack("Started")
            self.engine.register_event_in(REPORT_PERIOD_S, self.tick_send_report, self)
            Expect.slack_initialised = True

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

    def finish(self):
        if Expect.slack_initialised:
            self.post_to_slack("Stopped")
            Expect.slack_initialised = False
        super(Expect,self).finish()

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
        Expect.event_log.append( (rel_t, self.properties["$id"], event) )
        self.dump_events()
        
    def dump_events(self):
        s = ""
        for L in Expect.event_log:
            s += str(L[0]) + "," + str(L[1]) + "," + str(L[2]) + "\n"
        logging.info("Log of (un)expected events:\n"+s)

    def score(self):
        """Return a quality score of between 0.0 and 1.0."""
        if len(Expect.event_log)==0:
            return 1.0
        sum = 0
        for L in Expect.event_log:
            if L[2]==EVENT_IN_WINDOW:
                sum += 1
        sum = sum / float(len(Expect.event_log))

        return sum

    def create_histo(self):
        """Plot logged events as a set of histograms."""
        histo_in_window = [0] * HISTO_BINS
        histo_duplicate_event = [0] * HISTO_BINS
        histo_outside_window = [0] * HISTO_BINS
        histo_missing_event = [0] * HISTO_BINS
        period = self.expected_timefunction.period()
        for L in Expect.event_log:
            modulo_time = (float(L[0]) % period) / period # Normalise time to 0..1
            bin = int(HISTO_BINS * modulo_time)
            if L[2]==EVENT_IN_WINDOW:
                histo_in_window[bin] += 1
            elif L[2]==DUPLICATE_EVENT_IN_WINDOW:
                histo_duplicate_event[bin] += 1
            elif L[2]==EVENT_OUTSIDE_WINDOW:
                histo_outside_window[bin] += 1
            elif L[2]==MISSING_EVENT:
                histo_missing_event[bin] += 1
            else:
                assert False

        expected=[]
        for ti in range(HISTO_BINS):
            t = ti * float(period) / HISTO_BINS
            expected.append(self.expected_timefunction.state(t, t_relative=True))

        return (period, expected, [histo_in_window, histo_duplicate_event, histo_outside_window, histo_missing_event])

    def output_plot(self):
        histo = self.create_histo()
        div1 = plotting.plot_histo(histo[0], histo[1], histo[2])
        div2 = plotting.plot_score_log(Expect.score_log)
        plotting.write_page(self.instance_name, [div1, div2])
        
    def post_to_slack(self, text):
        if self.slack_webhook is not None:
            text = "{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " GMT " + text
            payload = {"text" : text,
                       "as_user" : False,
                       "username" : "Synth "+self.instance_name,
                       }
            try:
                response = requests.post(self.slack_webhook, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
            except httplib.HTTPException as err:
                logging.error("expect.post_to_slack() failed: "+str(err))

    def tick_send_report(self, _):
        Expect.score_log.append( (self.engine.get_now(), self.score() * 100) )

        self.output_plot()
        # self.post_to_slack("Synth histogram of expected vs. actual: "+url)
        self.engine.register_event_in(REPORT_PERIOD_S, self.tick_send_report, self)
        
