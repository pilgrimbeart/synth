#!/usr/bin/env python

# Google Map address look-up.
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

import os
import logging
import requests
import urllib

try:
    GOOGLE_API_KEY = os.environ('GOOGLE_API_KEY')
except AttributeError:
    GOOGLE_API_KEY = 'UNDEFINED'
    logging.error("No GOOGLE_API_KEY has been set.")


geo_cache = {}


def address_to_long_lat(address):
    """Get the longitude and latitude of an address from Google Maps.
    
    Args:
         address (string): Lookup string of the address.
     
    Returns:
        (float, float): Longitude and latitude of address.
        
    """
    global geo_cache
    if address in geo_cache:
        return geo_cache[address]

    query = '?' + urllib.urlencode({'key': GOOGLE_API_KEY}) + '&' + urllib.urlencode({'address': address})
    response = requests.get('https://maps.googleapis.com/maps/api/geocode/json' + query,
                            verify=True, headers={"Content-Type": "application/json"})
    data = response.json()

    geocode = data["results"][0]["geometry"]["location"]
    (lng, lat) = (geocode["lng"], geocode["lat"])

    geo_cache[address] = (lng, lat)
    return lng, lat
