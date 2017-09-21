"""measure: Make measurements on an event log.

    Scan an event log and make measurements on it.
    This module is intended to (eventually) be a functional equivalent
    to DevicePilot's query() endpoint, and thus able to regression-test it.

    This module can also be run on the command-line as a standalone utility, with input filename and other arguments.
"""

import re
import logging
import time

"""Query schema as of 2017-09-14:
  "op" = "history"  // List digested points
  "start" : <date>
  "end" : <date>
  {"select" : <select>}

  "op" = "eventify" // Lists rising and falling edges of a filter
  "start" : <date>
  "end" : <date>
  "filterStr" : ""
  {"select" : <select>}

  "op" = "last" // Bin points over time and return last digested point per device per bin
  "start" : <date>
  "end" : <date>
  {"select" : <select>}

  "op" = "count" // Bin points over time and return result counts of a value filter per bin
  "start" : <date>
  "end" : <date>
  "valueFilterStr" : ""
  {"select" : <select>}

  "op" = "duration/mean/min/max"  // keyed result aggregation of a value filter
  "start" : <date>
  "end" : <date>
  valueFilterStr : ""
  {"select" : <select>}
  {"timeseries" : boolean}
  {"keyFilterStr(s)" : ""}

  "op" = "at" // digested estate view or result counts of a value filter at time
  "at" = <date>
  {"select" = <select>}
  {"valueFilterStr = ""}

  "op" = "now" // digested estate view or result counts of a value filter at query time
  {"select" = <select>}
  {"valueFilterStr = ""}

  "op" = "new" // time of latest data

where:
  <date> : number (epochseconds) | string (ISO8601)

  <select> :
    "deviceId(s)" : "" or []
    "field(s)" : "" or []
    "scopeFilterStr" : ""
"""

TEST_FILE = "query_self_test_vectors.evt"


def evaluate(expression, prev,curr,succ):
    """Evaluate a JS expression, using property variables in <curr> dict. <prev> and <succ> are the same for the previous and following event, if any"""
    # Some DevicePilot property names begin with $ (e.g. $ts), but this isn't legal JS
    # so we convert $ to _ in both <expression> and <var_dict>
    def ago(secs):
        # Expressions like "$ts < ago(3600)" mean that if a timestamp hasn't been received for an hour then it's a timeout.
        # So ago() actually needs to look for the NEXT timestamp, if any.
        if succ==None:
            t = time.time() # If there is no following event, then now() really is now!
        else:
            t = succ["_ts"]
        return t - secs

    globls = {"ago" : ago}
    result = eval(expression,globls, curr)
    # print expression,"on",curr,"=>",result
    return result


def do_query(params, event_dict):
    """Run a query on an event log. We don't "understand" the key format of the event log
       (which might be created by e.g. evt2csv), we just rely on the fact it will sort into time order"""
    expression = params["expression"]
    logging.info("Running query ("+expression+")")

    # Rename property names like "$*" into "_*" so that evaluator can handle them as valid variable names
    expression = re.sub(r"\$","_", expression)

    # Create a dict of $ids, each of which will be a list of events
    events_by_id = {}
    for pairs in event_dict.values():
        for p,v in pairs:
            if p == "$id":
                id = v
                if id not in events_by_id:
                    events_by_id[id] = []
    
    # Fill lists by ID
    # (and rename $* to _*)
    for k in sorted(event_dict.keys()):
        props = {}
        for (p,v) in event_dict[k]:
            if p.startswith("$"):
                props["_"+p[1:]] = v
            else:
                props[p] = v
        events_by_id[props["_id"]].append(props)

    # Evaluate expression for each event
    for events in events_by_id.values():
        LEN = len(events)
        for n in range(LEN):
            if n==0:
                prev = None
            else:
                prev = events[n-1]
            curr = events[n]
            if n==LEN-1:
                succ = None
            else:
                succ = events[n+1]
            if evaluate(expression, prev,curr,succ):
                print curr

if __name__ == "__main__":
    import sys
    import evt2csv
    if len(sys.argv)<2:
        """If no args then do self-test"""
        evts = evt2csv.read_evt_file(TEST_FILE)
        params = {
            "expression" : "$ts < ago(30)"
            }
        do_query(params, evts)
        
##    for filename in sys.argv[1:] :
##        print "Converting ",filename
##        evt = read_evt_file(filename+".evt")
##        open(filename+"_converted.csv","wt").write(convert_to_csv(evt))
##    print "Done"
