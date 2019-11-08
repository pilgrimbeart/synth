#T!/usr/bin/env python
#
# Looks up historical weather data in Dark Sky
#
# Copyright (c) 2019 DevicePilot Ltd.
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

import json, httplib, urllib
import time
import logging

CACHE_FILE = "../synth_logs/dark_sky_cache.txt"
KEY_FILE = "../synth_accounts/default.json"
API_DOMAIN = "api.darksky.net"

HOUR = 60 * 60
DAY = HOUR * 24

if __name__ == "__main__":
    CACHE_FILE = "../../../" + CACHE_FILE
    KEY_FILE = "../../../" + KEY_FILE

# ==== Dark Sky API ====

def clear_caches():
    global caches
    caches = {"weather" : {}}

clear_caches()
try:
    logging.info("Powered by Dark Sky (tm)")    # Requirement of service to display this
    f = open(CACHE_FILE)
    caches = json.loads(f.read())
    f.close()
    logging.info("Used existing Dark Sky cache "+CACHE_FILE)
except:
    logging.warning("No existing Dark Sky cache")

account_key = None
try:
    f = open(KEY_FILE)
    kf = json.loads(f.read())
    f.close()
    account_key = kf["dark_sky_key"]
except:
    logging.error("Can't open Dark Sky key file")

def set_headers():
    """Sets the headers for sending to the server.

       We assume that the user has a token that allows them to login. """
    headers = {}
    headers["Content-Type"] = "application/json"
    return headers


def add_to_cache(cache, key, contents):
    caches[cache][key] = contents

def write_cache():
    if CACHE_FILE:
        s = json.dumps(caches)
        if len(s) > 1e7:
            logging.warning("Dark Sky cache file size is getting large: "+str(len(s))+" bytes")
        open(CACHE_FILE, "wt").write(s)
    else:
        logging.info("Not writing Dark Sky back to cache")

def round_time(epoch_seconds):
    # Round time to hourly resolution (so if multiple sim runs are done in quick succession, and with timing relative to real time, we don't do lots of lookups for times just a few minutes apart)
    return int(epoch_seconds/HOUR) * HOUR

def round_angle(angle):
    return int(angle * 1000) / 1000.0   # 3 decimal places is plenty for weather (about 100m)

def extract_and_cache(DS_results, latitude, longitude, epoch_seconds=None):
# Dark Sky returns a standard set of properties both for its "current" reading, and for hourly readings
# On any Time Machine request, it returns a days-worth of hourly readings, so by caching these we
# can reduce DS reads by a factor of 24
# The co-ordinates supplied as params are what the user requested (i.e. what to cache by), not necessarily the location that DS returns (which we ignore)
    if epoch_seconds is None:
        t = round_time(DS_results["time"])
    else:
        t = round_time(epoch_seconds)

    cache_key = str((latitude, longitude, t))
    result = {  # We asked for SI units, so...
        "external_temperature" : DS_results.get("temperature", 0.0), # C
        "wind_speed" : DS_results.get("windSpeed", 0.0), # m/s
        "precipitation_intensity" : DS_results.get("precipIntensity", 0.0), # mm/hour
        "precipitation_probability" : DS_results.get("precipProbability", 0.0), # 0..1
        "cloud_cover" : DS_results.get("cloudCover", 0.5),   # 0..1
        "humidity" : DS_results.get("humidity", 0.5)    # 0..1
        }

    add_to_cache("weather", cache_key, result)
    return result

def get_weather(latitude, longitude, epoch_seconds):
    epoch_seconds = round_time(epoch_seconds)
    latitude = round_angle(latitude)
    longitude = round_angle(longitude)
    cache_key = str((latitude, longitude, epoch_seconds))
    if cache_key in caches["weather"]:
        return caches["weather"][cache_key]

    logging.info("Looking up " + cache_key + " in Dark Sky")

    time_start = time.time()

    conn = httplib.HTTPSConnection(API_DOMAIN)
    URL = "/forecast/"+str(account_key)+"/"+str(latitude)+","+str(longitude)+","+str(epoch_seconds)+"?units=si&exclude=minutely,daily,flags"    # Using exclude apparently makes it a bit faster?
    conn.request('GET', URL, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()

    time_result = time.time()

    try:
        data = json.loads(result)
        result = extract_and_cache(data["currently"], latitude, longitude, epoch_seconds)   # Requested reading
        for r in data["hourly"]["data"]:
            extract_and_cache(r, latitude, longitude)   # Also cache info for other hours that DS has given us
        write_cache()
    except:
        logging.error(URL)
        logging.error(str(result))
        logging.error(json.dumps(data))
        raise

    time_end = time.time()

    t_fetch = time_result - time_start
    t_process = time_end - time_result
    if t_fetch > 1 or t_process > 1:
        logging.warning("(Dark Sky took "+str(time_fetch)+"s to fetch and "+str(time_process)+"s to process)")

    return result

def main():
    global CACHE_FILE, caches
    logging.basicConfig(level = logging.NOTSET)
    logging.info("Starting")
    t = 1552898857  # 08:47 on 18/03/2019
    (lat, lon) = (52.2053, 0.1218)  # Cambridge UK
    CACHE_FILE = None   # Don't read or write cache file during testing (but still cache during testing)
    clear_caches()
    for h in range(48):
        result = get_weather(lat, lon, t + h * HOUR)
        print result
 
if __name__ == "__main__":
    main()
