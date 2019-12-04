#!/usr/bin/env python
"""Generate global device co-ordinates which have statistics roughly matching technological population density."""
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

DEFAULT_POP_MAP = "dnb_land_ocean_ice.2012.13500x6750_grey.jpg"
# DEFAULT_POP_MAP = "dnb_land_ocean_ice.2012.13500x6750_britain_outline.jpg"
# DEFAULT_POP_MAP = "dplogo.jpg"
# DEFAULT_POP_MAP = "norwich.jpg"
# DEFAULT_POP_MAP = "britain.jpg"
# DEFAULT_POP_MAP = "usa.jpg"

# import logging # Emitting any log messages in this module suppresses all other log output - I have NO idea why
import os, sys
import logging
from PIL import Image # To get this on Linux, suggest using "sudo apt-get install python-imaging"
Image.MAX_IMAGE_PIXELS = 1000000000 # We're dealing with large images, so prevent DecompressionBomb errors
import numpy
import random
import math
from .google_maps import address_to_lon_lat, lon_lat_to_address


MINLON = 100000
MAXLON = -10000
MINLAT  = 100000
MAXLAT  = -10000
MINX = 100000
MAXX = -100000
MINY = 100000
MAXY = -100000

class point_picker():
    myRandom = random.Random()  # Use our own private random-number generator, so we will repeatably generate the samepoints regardless of who else is asking for random numbers (useful to keep point data stable, because of caching weather or maps results)
    myRandom.seed(1234)

    """This uses a huge amount of memory. So strongly recommend deleting after use.""" 
    def __init__(self, population_map=None):
        if population_map is None:
            population_map = DEFAULT_POP_MAP
        else:
            logging.info("Using custom population map "+str(population_map))
        # Load map
        module_local_dir = os.path.dirname(__file__)
        im = Image.open(os.path.join(module_local_dir, population_map))
        self.arr = numpy.asarray(im)
        self.xlimit, self.ylimit = float(len(self.arr[0])), float(len(self.arr))
        # print "Loaded image of size",self.xlimit,"x",self.ylimit
        # print "Pixel range:",numpy.amin(self.arr), numpy.amax(self.arr)
        # self.arr = self.arr / 255.0 # We used to normalise the "uint8" pixels into floating point - but explodes memory usage by x8!
        # Set area to choose from
        self.area = None

        # logging.info("Image size is "+str(self.arr.nbytes / (1024*1024))+" MB")

        
    def set_area(self, area, google_maps_key):
        """If <area> is defined it must be two strings: ["centre","edge"].
        Each string is an address (e.g. "Cambridge, UK") which is looked-up to get lat/lon.
        These are then used to define the centre and edge of an allowable circle to pick within"""
        # Pathologies:
        # . Asking for an area which contains zero population will spin forever
        # . Providing a huge map with a tiny populated area will be very slow
        # . The circle is a lon/lat circle. So on most map projections it will look circular over the equator, but an increasingly vertical oval towards the poles (e.g. UK).
        self.area = area

        area_centre, area_edge = address_to_lon_lat(area[0], google_maps_key), address_to_lon_lat(area[1], google_maps_key)
        self.area_centre_xy, self.area_edge_xy = self.lon_lat_to_xy(area_centre), self.lon_lat_to_xy(area_edge)
        self.area_radius_pixels = math.sqrt(math.pow(self.area_centre_xy[0]-self.area_edge_xy[0], 2) + math.pow(self.area_centre_xy[1]-self.area_edge_xy[1],2))

        
    def xy_to_lon_lat(self, coords):
        """Normalise axes to +/-1"""
        y = (2*coords[1]/self.ylimit)-1.0
        x = (2*coords[0]/self.xlimit)-1.0

        # Longitude ranges from -180 degrees (East) to 180 degrees (West)
        # Latitude ranges from +90 degrees (North pole) to -90 degrees (South pole)

        longitude = x * 180.0
        latitude = y * -90.0    # (y goes down, latitude goes up)

        return (longitude, latitude)

    def lon_lat_to_xy(self, coords):
        """Reduce to +/-1"""
        x = coords[0] / 180.0
        y = coords[1] / -90.0

        x = ((x+1.0)/2.0) * self.xlimit
        y = ((y+1.0)/2.0) * self.ylimit

        x = max(min(x,self.xlimit), 0)
        y = max(min(y,self.ylimit), 0)

        # logging.info("lon_lat_to_xy "+str(coords)+" -> "+str((x,y)))
        return (x,y)
        
    def pick_point(self, area=None, google_maps_key=None):
        """Returns a (latitude,longitude) point, on population map, within area"""
        global MINLON, MAXLON, MINLAT, MAXLAT, MINX, MAXX, MINY, MAXY

        if area==None:
            self.area = None
        else:
            self.set_area(area, google_maps_key)
        
        while True:
            if self.area:
                # logging.info("area_radius_pixels="+str(self.area_radius_pixels))
                radius = point_picker.myRandom.random() * self.area_radius_pixels
                angle = point_picker.myRandom.random() * 2 * math.pi
                ox = math.sin(angle) * radius
                oy = math.cos(angle) * radius
                # logging.info("ox,oy="+str((ox,oy)))
                x_float = self.area_centre_xy[0] + ox
                y_float = self.area_centre_xy[1] + oy
                # logging.info("x,y_float="+str((x_float, y_float)))
            else:
                x_float, y_float = point_picker.myRandom.randrange(0, self.xlimit-1), point_picker.myRandom.randrange(0, self.ylimit-1)
            x_int, y_int = int(x_float), int(y_float)
            v = (self.arr[y_int][x_int] / 255.0)
            if v > point_picker.myRandom.random():
                break

        # Dither our pixels, otherwise all points will be on pixel grid
        # x += point_picker.myRandom.random()
        # y += point_picker.myRandom.random()

        longitude,latitude = self.xy_to_lon_lat((x_float, y_float))
        # logging.info("longitude, latitude = "+str((longitude, latitude)))

        MINLAT = min(MINLAT, latitude)
        MAXLAT = max(MAXLAT, latitude)
        MINLON = min(MINLON, longitude)
        MAXLON = max(MAXLON, longitude)
        MINX = min(MINX,x_float)
        MAXX = max(MAXX,x_float)
        MINY = min(MINY,y_float)
        MAXY = max(MAXY,y_float)
        # print "x,y=",x,y," longitude,latitude=",longitude,latitude
        # logging.info("pick_point returning "+str((longitude, latitude)))
        return (longitude, latitude)

    def pick_points(self, n=1):
        L = []
        for i in range(n):
            L.append(self.pick_point())
        return L

def main():
    p = point_picker()
    L = p.pick_points(n=1000, area=["London,UK","Cambridge,UK"])

    print("LONG:",MINLON, MAXLON,"DIFF",MAXLON-MINLON)
    print("LAT:",MINLAT, MAXLAT,"DIFF",MAXLAT-MINLAT)
    print("X:",MINX, MAXX,"DIFF",MAXX-MINX)
    print("Y:",MINY, MAXY,"DIFF",MAXY-MINY)

class geo_pick():
# Slightly easier parameter-picking
    # Class variables
    map_file = None
    pp = None

    def __init__(self, context, params):
        self.generate_addresses = params.get("generate_addresses", False)
        self.area_centre = params.get("area_centre", None)
        self.area_radius = params.get("area_radius", None)
        self.map_file = params.get("map_file", None)
        if (geo_pick.pp is None) or (geo_pick.map_file != self.map_file):  # Only load map at start, or if changed, as very expensive operation
            geo_pick.pp = point_picker(self.map_file)  # Very expensive, so do only once
            geo_pick.map_file = self.map_file

        self.area = None
        if self.area_centre != None:
            self.area = [self.area_centre, self.area_radius]
        self.google_maps_key = context.get("google_maps_key", None)

    def pick(self):
        (self.lon,self.lat) = geo_pick.pp.pick_point(self.area, self.google_maps_key)
        return (self.lon,self.lat)

    def addresses(self):
        if not self.generate_addresses:
            return []
        return lon_lat_to_address(self.lon, self.lat, self.google_maps_key).items()


if __name__ == "__main__":
    main()
