# Read grid carbon intensity from National Grid
# For some unexplained reason a considerable amount of the data seems to be arranged so that when you ask for a day, you get a day shifted an hour early, i.e. the last hour from the previous day, and not the last hour from today.
# This is not explained by DST, as it happens in the winter (it happens for the whole of 2021 but not e.g. 2018)
# The actual day reported in the data is correct. Therefore if we can't find the data where we expect to, we look in the following day too

from datetime import datetime
import requests
import json
from common import ISO8601
import logging

API_DOMAIN = "api.carbonintensity.org.uk"
API_URL = "/intensity/date/"

DELAY_AFTER_HALF_HOUR_BEFORE_READING = 15

CACHE_FILE = "../synth_logs/gridcarbon_cache.txt"
g_cache = None

def isodate(epoch_s):
    return datetime.fromtimestamp(epoch_s).isoformat()

def load_cache():
    global g_cache
    try:
        f = open(CACHE_FILE)
        g_cache = json.loads(f.read())
        f.close()
        logging.info("Used existing grid carbon cache " + CACHE_FILE)
    except:
        logging.warning("No existing grid carbon cache, starting new one")
        g_cache = {}

def read_cache(t):
    global g_cache
    if g_cache is None:
        load_cache()    
    
    return g_cache.get(isodate(t), None)

def write_cache(t, value):
    global g_cache
    if g_cache is None:
        load_cache()

    g_cache[isodate(t)] = value

    s = json.dumps(g_cache)
    if len(s) > 1e7:
        logging.warning("Grid carbon cache file size is getting large: "+str(len(s))+" bytes")
    open(CACHE_FILE, "wt").write(s)

def roundit(epoch_s, M):
    # We know that National Grid API emits readings every half an hour
    # We therefore round the time to M minutes *past* the half hour, to give time for the value to have changed (avoid race condition around the actual boundary)
    dt = datetime.fromtimestamp(epoch_s)
    if dt.minute >= M+30:
        dt = dt.replace(minute = M+30)
    else:
        dt = dt.replace(minute = M)
    dt = dt.replace(second = 0, microsecond = 0)
    return dt.timestamp()
    
def prev_tick(epoch_s):
    """Given a time, when did the value last change?"""
    return roundit(epoch_s, DELAY_AFTER_HALF_HOUR_BEFORE_READING)

def next_tick(epoch_s):
    """Given a time, when will value next change?"""
    return roundit(epoch_s + 60*30, DELAY_AFTER_HALF_HOUR_BEFORE_READING) # Return next half-hour

def find_intensity(epoch_s, look_in_next_day=False):
    """epoch_s must be rounded to a half-hour"""
    if look_in_next_day:
        adder = 60*60*24
    else:
        adder = 0
    iso_day = datetime.fromtimestamp(epoch_s + adder).isoformat()[0:10]
    iso_day_and_time = datetime.fromtimestamp(epoch_s).isoformat()[0:16]    # Just up to the minutes
    url = "https://" + API_DOMAIN + API_URL + iso_day  # API takes just the day
    halfhours = json.loads(requests.get(url).text)["data"]

    for hh in halfhours:
        if(hh["from"].startswith(iso_day_and_time)):
            if hh["intensity"]["actual"] is not None:   # If there is no actual value
                return (hh["intensity"]["actual"], False)
            else:
                return (hh["intensity"]["forecast"], True)      # then use the forecasted one (this can happen if you ask too close to "now")
    return (None, False)

def get_intensity(epoch_s):
    """Given a time, find the reported grid carbon"""
    t = roundit(epoch_s, 0) # Round to actual half-hour, as that's what's reported

    intensity = read_cache(t)
    if intensity is not None:
        return intensity

    (intensity, forecasted) = find_intensity(t, look_in_next_day=False)   # Look in expected day
    if intensity is None:                                   # If can't find it, try day after (since some days seem to be stored as 11pm-11pm)
        (intensity, forecasted) = find_intensity(t, look_in_next_day=True)

    if (intensity is not None): # This should say "and not forecasted", but we so often want to know the carbon intensity "now" that this would thrash the API
        write_cache(t, intensity)

    return intensity

if __name__ == "__main__":
    def test(datestr):
        print(datestr,":",get_intensity(ISO8601.to_epoch_seconds(datestr)))

    test("2018-01-01T00:00:00")
    test("2018-01-01T00:00:01")
    test("2018-01-01T00:01:00")
    test("2018-01-01T00:29:00")
    test("2018-01-01T00:30:00")
    test("2018-01-01T00:31:00")
    test("2018-01-01T00:59:00")
    test("2018-01-01T01:00:00")
    test("2018-01-01T01:01:00")
    test("2018-01-01T01:30:00")
    test("2021-01-02T03:04:05")
    test("2021-01-01T23:59:00")
    test("2022-01-25T00:00:00")
    test("2022-01-25T17:00:00")
