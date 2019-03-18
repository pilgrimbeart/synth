#!/usr/bin/env python
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
import logging

CACHE_FILE = "../synth_logs/dark_sky_cache.txt"
KEY_FILE = "../synth_accounts/default.json"
API_DOMAIN = "api.darksky.net"

if __name__ == "__main__":
    CACHE_FILE = "../../../" + CACHE_FILE
    KEY_FILE = "../../../" + KEY_FILE

def set_headers():
    """Sets the headers for sending to the server.

       We assume that the user has a token that allows them to login. """
    headers = {}
    headers["Content-Type"] = "application/json"
    return headers


# ==== Dark Sky API ====

try:
    f = open(CACHE_FILE)
    caches = json.loads(f.read())
    f.close()
    logging.info("Used existing Dark Sky cache "+CACHE_FILE)
except:
    logging.info("No existing Dark Sky cache")
    caches = {"weather" : {}}

try:
    f = open(KEY_FILE)
    kf = json.loads(f.read())
    f.close()
    account_key = kf["dark_sky_key"]
except:
    logging.error("Can't open Dark Sky key file")
    account_key = None

def add_to_cache(cache, key, contents):
    caches[cache][key] = contents
    f = open(CACHE_FILE, "wt")
    f.write(json.dumps(caches))
    f.close()

def get_weather(latitude, longitude, epoch_seconds):
    if (str((latitude,longitude))) in caches["weather"]:
        return caches["weather"][str((latitude, longitude))]    # Avoid thrashing Dark Sky

    logging.info("Looking up "+str((latitude, longitude))+" in Dark Sky")
    conn = httplib.HTTPSConnection(API_DOMAIN)
    URL = "/forecast/"+str(account_key)+"/"+str(latitude)+","+str(longitude)+","+str(epoch_seconds)+"?units=si"
    # URL += '&' + urllib.urlencode({'key':google_maps_api_key})
    conn.request('GET', URL, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()
    try:
        data = json.loads(result)["currently"]
        result = {  # We asked for SI units, so...
                "temperature" : data["temperature"], # C
                "cloud_cover" : data["cloudCover"], # 
                "humidity" : data["humidity"], # 0..1
                "wind_gust" : data["windGust"], # m/s
                "wind_speed" : data["windSpeed"], # m/s
                "wind_bearing" : data["windBearing"], # degrees
                "precipitation_intensity" : data["precipIntensity"], # mm/hour
                "precipitation_probability" : data["precipProbability"] # 0..1
                }
    except:
        logging.error(URL)
        logging.error(json.dumps(data))
        raise
    add_to_cache("weather", str((latitude, longitude)), result)
    return result

def main():
    t = 1552898857  # 08:47 on 18/03/2019
    (lat, lon) = (52.2053, 0.1218)  # Cambridge UK
    print "get_weather returned ",get_weather(lat, lon, t)
 
if __name__ == "__main__":
    main()
