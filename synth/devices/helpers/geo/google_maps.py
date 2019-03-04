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

import json, httplib, urllib
import logging

def set_headers():
    """Sets the headers for sending to the DM server.

       We assume that the user has a token that allows them to login. """
    headers = {}
    headers["Content-Type"] = "application/json"
    return headers


# ==== Google Maps API ====
geo_cache = {}

def address_to_lon_lat(address, google_maps_api_key=None):
    global geo_cache
    if address in geo_cache:
        return geo_cache[address]    # Avoid thrashing Google (expensive!)

    (lng,lat) = (None, None)

    logging.info("Looking up "+str(address)+" in Google Maps")
    conn = httplib.HTTPSConnection("maps.google.com")   # Must now use SSL
    URL = '/maps/api/geocode/json' + '?' + urllib.urlencode({'address':address})
    if google_maps_api_key is None:
        logging.info("No Google Maps key so Google maps API may limit your requests")
    else:
        URL += '&' + urllib.urlencode({'key':google_maps_api_key})
    conn.request('GET', URL, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()
    try:
        data = json.loads(result)
        geo = data["results"][0]["geometry"]["location"]
    except:
        logging.error(URL)
        logging.error(json.dumps(data))
        raise
    (lng,lat) = (geo["lng"], geo["lat"])
    geo_cache[address] = (lng,lat)
    return (lng,lat)


LL_cache = {}

useful_fields = ["street_number", "route", "locality", "postal_town", "administrative_area_level_2", "administrative_area_level_1", "country", "postal_code"]


def intersect_lists(L1, L2):
    L = list(set(L1).intersection(set(L2)))
    if len(L)==0:
        return None
    return L[0] # Assumes there is never more than one item in intersection

def lon_lat_to_address(lng, lat, google_maps_api_key=None):
    global LL_cache
    s = str((lng,lat))
    if s in LL_cache:
        return LL_cache[s]    # Avoid thrashing Google (expensive!)

    logging.info("Looking up "+str((lng,lat))+" in Google Maps")
    conn = httplib.HTTPSConnection("maps.google.com")   # Must now use SSL
    URL = '/maps/api/geocode/json' + '?' + urllib.urlencode({'latlng' : str(lat)+","+str(lng)})
    if google_maps_api_key is None:
        logging.info("No Google Maps key so Google maps API may limit your requests")
    else:
        URL += '&' + urllib.urlencode({'key':google_maps_api_key})
    conn.request('GET', URL, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()
    try:
        data = json.loads(result)
        fields = data["results"][0]["address_components"]
        results = {}
        for k in fields:
            L = intersect_lists(useful_fields, k["types"])
            if L != None:
                results.update({"address_"+L : k["long_name"]})
    except:
        logging.error(URL)
        logging.error(json.dumps(data))
        raise
    LL_cache[str((lng,lat))] = results
    return results

def main():
    address = "Cambridge, UK"
    lon,lat = address_to_lon_lat(address)
    print "For address",address,"Lon,Lat = ",lon,lat
 
if __name__ == "__main__":
    main()
