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

CACHE_FILE = "../synth_logs/geo_cache.txt"

def set_headers():
    """Sets the headers for sending to the DM server.

       We assume that the user has a token that allows them to login. """
    headers = {}
    headers["Content-Type"] = "application/json"
    return headers


# ==== Google Maps API ====

try:
    f = open(CACHE_FILE)
    caches = json.loads(f.read())
    f.close()
    logging.info("Used existing Google Maps cache "+CACHE_FILE)
except:
    logging.info("No existing Google Maps cache")
    caches = {"geo" : {}, "reverse" : {}, "route" : {}}

def add_to_cache(cache, key, contents):
    caches[cache][key] = contents
    try:
        f = open(CACHE_FILE, "wt")
        f.write(json.dumps(caches))
        f.close()
    except Exception as exc:
        print exc

def address_to_lon_lat(address, google_maps_api_key=None):
    if address in caches["geo"]:
        return caches["geo"][address]    # Avoid thrashing Google (expensive!)

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
    add_to_cache("geo", address, (lng,lat))
    return (lng,lat)


useful_fields = ["street_number", "route", "locality", "postal_town", "administrative_area_level_2", "administrative_area_level_1", "country", "postal_code"]


def intersect_lists(L1, L2):
    L = list(set(L1).intersection(set(L2)))
    if len(L)==0:
        return None
    return L[0] # Assumes there is never more than one item in intersection

def lon_lat_to_address(lng, lat, google_maps_api_key=None):
    s = str((lng,lat))
    if s in caches["reverse"]:
        return caches["reverse"][s]    # Avoid thrashing Google (expensive!)

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
        results = {}
        if data["status"] != "ZERO_RESULTS":
            fields = data["results"][0]["address_components"]
            for k in fields:
                L = intersect_lists(useful_fields, k["types"])
                if L != None:
                    results.update({"address_"+L : k["long_name"]})
    except:
        logging.error(URL)
        logging.error(json.dumps(data))
        raise
    add_to_cache("reverse", str((lng,lat)), results)
    return results

# https://maps.googleapis.com/maps/api/directions/json?origin=Tesco%2CWalkden%2CUK&destination=Manchester%2CUK&mode=walking&key=AIzaSyDF6uyDi5Nq6EQ58FrViRv1JTs-1ZtQF6o

# result.status == "OK"
# for step in result.routes[0].legs[0].steps:
    # step.duration.value (seconds)
    # step.start_location["lat"]  ["lng"]
    # step.end_location["lat"]  ["lng"]


def get_route_from_lat_lons(from_lat, from_lng, to_lat, to_lng, mode="walking", google_maps_api_key=None):
    hash = str((from_lat, from_lng, to_lat, to_lng))
    if hash in caches["route"]:
        return caches["route"][hash]

    logging.info("Looking up route "+hash+" in Google Maps")
    conn = httplib.HTTPSConnection("maps.googleapis.com")
    URL = '/maps/api/directions/json' + '?mode='+str(mode)
    URL += '&origin='+str(from_lat)+","+str(from_lng)
    URL += "&destination="+str(to_lat)+","+str(to_lng)
    if google_maps_api_key is None:
        logging.info("No Google Maps key so Google maps API may limit your requests")
    else:
        URL += '&' + urllib.urlencode({'key':google_maps_api_key})
    print "URL is "+URL
    conn.request('GET', URL, None, set_headers())
    resp = conn.getresponse()
    result = resp.read()
    try:
        data = json.loads(result)
        assert data["status"] == "OK"
        route = []
        for step in data["routes"][0]["legs"][0]["steps"]:
            route.append( {
                "start_lat" : step["start_location"]["lat"],
                "start_lng" : step["start_location"]["lng"],
                "end_lat"   : step["end_location"]["lat"],
                "end_lng"   : step["end_location"]["lng"],
                "duration" : step["duration"]["value"]    # seconds
                })

    except:
        logging.error(URL)
        logging.error(json.dumps(data))
        raise
    add_to_cache("route", hash, route)
    return route 
     

def main():
    key = json.loads(open("../../../../synth_accounts/default.json","rt").read())["google_maps_key"]
    from_lon, from_lat = address_to_lon_lat("Cambridge, UK", google_maps_api_key=key)
    to_lon, to_lat = address_to_lon_lat("Oxford, UK", google_maps_api_key=key)
    route = get_route_from_lat_lons(from_lat, from_lon, to_lat, to_lon, google_maps_api_key=key)
    print "route:",route
 
if __name__ == "__main__":
    import os
    cwd = os.getcwd()
    print cwd
    main()


