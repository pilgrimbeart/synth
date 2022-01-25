#!/usr/bin/env python
"""
Top-level module for the DevicePilot Synth project.
Generate and exercise synthetic devices for testing and demoing IoT services.
"""
#
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
import os
import time, sys, json, re, traceback
import signal
import requests
import random   # Might want to replace this with something we control
from datetime import datetime
from common import ISO8601
from common import importer
from events import Events
import device_factory
import zeromq_rx, zeromq_tx
from directories import *
import faulthandler

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

g_get_sim_time = None   # TODO: Find a more elegant way for logging to discover simulation time
g_slack_webhook = None
g_instance_name = None
g_asked_to_pause = False

# Set up Python logger to report simulated time
def in_simulated_time(self,secs=None):
    if g_get_sim_time:
        t = g_get_sim_time()
    else:
        t = 0
    return ISO8601.epoch_seconds_to_datetime(t).timetuple()  # Logging might be emitted within sections where simLock is acquired, so we accept a small chance of duff time values in log messages, in order to allow diagnostics without deadlock

def init_logging(params):
    global g_slack_webhook
    
    # Log to console
    logging.getLogger('').handlers = [] # Because of the (dumb) way that the logging module is built, if anyone, anywhere, during e.g. import, calls basicConfig, then we're screwed
    logging.basicConfig(level=logging.INFO,
                    format=LOG_FORMAT,
                    datefmt='%Y-%m-%dT%H:%M:%S'
                    )
    logging.Formatter.converter = in_simulated_time # Make logger use simulated time

    # Log to file
    try:
        os.mkdir(LOG_DIR)	# Ensure directory exists, first time through
    except:
        pass
    file_handler = logging.FileHandler(filename=LOG_DIR + g_instance_name + ".out", mode="w")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    h2 = logging.getLogger().addHandler(file_handler)

    # Log to Slack
    g_slack_webhook = params.get("slack_webhook", None)

def post_to_slack(text):
    if g_slack_webhook is not None:
        text = "{:%Y-%m-%d %H:%M:%S}".format(datetime.now()) + " GMT " + text
        payload = {"text" : text,
                   "as_user" : False,
                   "username" : "Synth "+g_instance_name,
                   }
        try:
            response = requests.post(g_slack_webhook, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        except Exception as err:
            logging.error("post_to_slack() failed: "+str(err))

def merge(a, b, path=None): # From https://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107
    """Deep merge dict <b> into dict <a>, overwriting a with b for any overlaps"""
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            else:
                ps = ".".join(path)
                if path != []:
                    ps += "."
                logging.warning("Overwriting "+str(ps)+str(key)+" with "+str(b[key])+" (was "+str(a[key])+")")
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def readParamfile(filename, fail_silently=False):
    s = "{}"
    try:
        s = open(SCENARIO_DIR+filename+".json","rt").read()
    except:
        try:
            s = open(ACCOUNTS_DIR+filename+".json","rt").read()
        except:
            if not fail_silently:
                raise
    return s

def remove_C_comments(string):
    """Remove C and C++ comments (therefore also Javascript comments)"""
    # As per https://stackoverflow.com/questions/2319019/using-regex-to-remove-comments-from-source-files#18381470
    pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
    # first group captures quoted strings (double or single)
    # second group captures comments (//single-line or /* multi-line */)
    regex = re.compile(pattern, re.MULTILINE|re.DOTALL)
    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return "" # so we will return empty to remove the comment
        else: # otherwise, we will return the 1st group
            return match.group(1) # captured quoted-string
    return regex.sub(_replacer, string)

def preprocess(s):
    """deal with #define statements"""
    output = []
    macros = {}
    lines = s.split("\n")
    defining_macro = False
    for L in lines:
        if L.startswith("#define"):
            defining_macro = True
            macro_name = L[8:]
            macros[macro_name] = ""
        elif L.startswith("#enddef"):
            assert defining_macro
            defining_macro = False
        else:
            if defining_macro:
                macros[macro_name] = macros[macro_name] + L + "\n"
            else:
                for m in macros:
                    L = L.replace(m, macros[m])
                output.append(L)

    result = "\n".join(output)
    return result

def get_params():
    """Read command-line to ingest parameters and parameter files"""
    def macro(matchobj):
        s = matchobj.group(0)[3:-3] # Remove <<<anglebrackets>>>
        if s not in params:
            raise ValueError("undefined macro: %s" % s)
        return params[s]

    def load_param_file(file, params, fail_silently=False):
        global g_instance_name

        logging.info("Loading parameter file "+file)
        s = readParamfile(file, fail_silently)
        s = preprocess(s)
        s = remove_C_comments(s) # Remove Javascript-style comments
        # We no-longer support Python-style comments, because interferes with auto-numbering in models s = re.sub("#.*$",  "", s, flags=re.MULTILINE) # Remove Python-style comments
        s = re.sub('<<<.*?>>>', macro, s)    # Do macro-substitution. TODO: Do once we've read ALL param files
        open("../synth_logs/latest.json", "wt").write(s+"\n (from "+file+")\n")  # If we get a parsing error, output the processed file so we can find the line & column easily
        j = json.loads(s)
        if "client" in j:   # We inherit the instance name from whichever file specifies the client
            g_instance_name = file
            logging.info("Naming this instance '" + str(g_instance_name) + "'")
        params = merge(params, j)

    if len(sys.argv) < 2:
        print("Usage: "+sys.argv[0]+" {filenames}   where filenames are one or more parameter files in scenarios/ or ../synth_accounts/\nSee https://devicepilot-synth.readthedocs.io")
        sys.exit(1)
        
    params = {}
    load_param_file("default", params, fail_silently=True)
    for arg in sys.argv[1:]:
        if arg.startswith("{"):
            logging.info("Setting parameters "+arg)
            params = merge(params, json.loads(arg))
        elif "=" in arg:    # RHS always interpreted as a string
            logging.info("Setting parameter "+arg)
            (key,value) = arg.split("=",1)  # split(,1) so that "a=b=c" means "a = b=c"
            params = merge(params, { key : value })
        else:
            load_param_file(arg, params)
    return params    

def signal_catcher(signal_received, frame):
    global g_asked_to_pause
    logging.info("Received signal "+str(signal_received))
    if signal_received == signal.SIGUSR1:
        logging.info("Pause requested")
        g_asked_to_pause = True
    logging.info("FYI Python stack is:")
    tb = traceback.format_list(traceback.extract_stack())
    for L in tb:
        L = L.replace("\n",": ")
        logging.info(L)

def install_signal_catcher():
    signal.signal(signal.SIGUSR1, signal_catcher)
    signal.signal(signal.SIGUSR2, signal_catcher)

def main():
    global g_get_sim_time
    global g_instance_name
    global g_asked_to_pause
    
    def incomingAsyncEvent(packet):    # CAUTION: Called asynchronously from the ZeroMQ rx thread
        if "action" in packet:
            if packet["action"] == "event":
                if packet["headers"]["Instancename"] == g_instance_name:
                    engine.register_event_in(0, device_factory.external_event, packet, None)
            elif packet["action"] == "announce":
                logging.log(packet["severity"], "[broadcast message] "+packet["message"])
            elif packet["action"] == "command":
                if packet["headers"]["Instancename"] == g_instance_name:
                    argv = packet["argv"]
                    logging.info("Received async command " + str(argv))
                    if len(argv) > 0:
                        client.async_command(argv)

    def event_count_callback():
        return events.event_count

    logging.getLogger().setLevel(logging.INFO)
    os.makedirs("../synth_logs", exist_ok = True)
    os.makedirs("../synth_accounts", exist_ok = True)

    params = get_params()
    assert g_instance_name is not None, "Instance name has not been defined, but this is required for logfile naming"
    init_logging(params)
    logging.info("*** Synth starting at real time "+str(datetime.now())+" ***")
    logging.info("Parameters:\n"+json.dumps(params, sort_keys=True, indent=4, separators=(',', ': ')))
    post_to_slack("Started")

    install_signal_catcher()

    Tstart = time.time()                # Human time
    Tstart_process = time.process_time()   # Time CPU usage
    random.seed(12345)  # Ensure reproduceability

    if not "client" in params:
        logging.error("No client defined to receive simulation results")
        return
    client = importer.get_class('client', params['client']['type'])(g_instance_name, params, params['client'])

    if not "engine" in params:
        logging.error("No simulation engine defined")
        return
    engine = importer.get_class('engine', params['engine']['type'])(params['engine'], client.enter_interactive, event_count_callback)
    g_get_sim_time = engine.get_now_no_lock

    if not "events" in params:
        logging.warning("No events defined")
    events = Events(client, engine, g_instance_name, params, params["events"])

    zeromq_rx.init(incomingAsyncEvent, emit_logging=True)
    zeromq_tx.init(emit_logging=True)

    logging.info("Simulation starts")

    faulthandler.dump_traceback_later(600, repeat=True) # TEMP - every 10 minutes emit a stack trace for every thread - to diagnose hanging issue
    err_str = ""
    try:
        while engine.events_to_come():
            engine.next_event()
            client.tick()
            if g_asked_to_pause:
                g_asked_to_pause = False
                logging.info("Paused")
                signal.pause()  # Suspend this process. Receiving any signal will then cause us to resume
                logging.info("Resuming")
        device_factory.close()
    except:
        err_str = traceback.format_exc()  # Report any exception, but continue to clean-up anyway
        logging.error("Error at real time "+str(datetime.now())+" (local)")
        logging.error(err_str)

    logging.info("Simulation ends")
    logging.info("Ending device logging ("+str(len(device_factory.g_devices))+" devices were emulated)")
    events.flush()
    client.close()

    logging.info("Elapsed real time: " + str(int(time.time()-Tstart))+" seconds.")
    logging.info("CPU time used: " + str(int(time.process_time()-Tstart_process))+" seconds.")

    if err_str=="":
        post_to_slack("Finished OK")
        exit(0)
    post_to_slack(err_str)
    exit(-1)

def check_install():
    if os.path.exists("../synth_logs") and os.path.exists("../synth_accounts"):
        return

    print("For further info please see https://devicepilot-synth.readthedocs.io/")
    if input("Missing log directory - would you like me to set up directories? (y/n)").lower().strip()[0] == "y":
        os.makedirs("../synth_logs", exist_ok = True)
        os.makedirs("../synth_accounts", exist_ok = True)
        if not os.path.exists("../synth_logs/OnFStest.json"):
            open("../synth_accounts/OnFStest.json", "wt").write('{\n    "client" : {\n        "type" : "filesystem",\n        "filename" : "OnFStest"\n    }\n}')
        print("Done.")
        print("Please try again.")
    exit()

if __name__ == "__main__":
    print("Synth")
    print("Running on Python"+str(sys.version_info.major)+"."+str(sys.version_info.minor))
    assert sys.version_info.major >= 3, "Synth must be run with python3 or higher"

    check_install()

    if False:    # Profile
        import cProfile, pstats
        cProfile.run('main()', 'profiling')
        p = pstats.Stats('profiling')
        p.sort_stats('cumulative').print_stats(30)
    else:
        main()
