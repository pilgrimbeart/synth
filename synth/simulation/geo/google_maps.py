#!/usr/bin/env python
#
# Looks up Google Maps
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

import httplib
import json
import urllib

GOOGLE_MAPS_API_KEY = open("../synth_certs/googlemapskey", "rt").read().strip()


def set_headers():
    """ Sets the headers for sending to the DM server. We assume that the
        user has a token that allows them to login. """
    headers = {"Content-Type": "application/json"}
    return headers


# ==== Google Maps API ====
geoCache = {}


def address_to_long_lat(address):
    global geoCache
    if address in geoCache:
        return geoCache[address]  # Avoid thrashing Google (expensive!)

    (lng, lat) = (None, None)

    # try:
    conn = httplib.HTTPSConnection("maps.google.com")  # Must now use SSL
    url = '/maps/api/geocode/json' + '?' + urllib.urlencode({'key': GOOGLE_MAPS_API_KEY}) + '&' + urllib.urlencode(
        {'address': address})
    conn.request('GET', url, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()
    data = json.loads(result)
    # print "For address "+address+" response from maps.google.com is "+str(data)
    geo = data["results"][0]["geometry"]["location"]
    (lng, lat) = (geo["lng"], geo["lat"])
    # except:
    # print "FAILED to do Google Maps lookup on location "+str(address)
    geoCache[address] = (lng, lat)
    return lng, lat


def main():
    address = "Cambridge, UK"
    lon, lat = address_to_long_lat(address)
    print "For address", address, "Lon,Lat = ", lon, lat


if __name__ == "__main__":
    main()
