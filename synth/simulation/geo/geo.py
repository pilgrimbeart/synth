#!/usr/bin/env python
#
# Generates global device co-ordinates which have statistics roughly matching technological population density
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
import math
import os
from random import randint, random

import numpy
from PIL import Image  # To get this on Linux, suggest using "sudo apt-get install python-imaging"

from google_maps import address_to_long_lat

DEFAULT_POP_MAP = "dnb_land_ocean_ice.2012.13500x6750_grey.jpg"
Image.MAX_IMAGE_PIXELS = 1000000000  # We're dealing with large images, so prevent DecompressionBomb errors

MINLONG = 100000
MAXLONG = -10000
MINLAT = 100000
MAXLAT = -10000
MINX = 100000
MAXX = -100000
MINY = 100000
MAXY = -100000


class PointPicker:  # It uses a huge amount of memory. So strongly recommend
    def __init__(self, population_map=DEFAULT_POP_MAP):
        self.area_centre, self.area_edge = 0, 0
        # Load map
        self.areaCentreXY, self.areaEdgeXY = self.lon_lat_to_x_y(self.area_centre), self.lon_lat_to_x_y(self.area_edge)
        self.areaRadiusPixels = math.sqrt(
            math.pow(self.areaCentreXY[0] - self.areaEdgeXY[0], 2) + math.pow(self.areaCentreXY[1] - self.areaEdgeXY[1],
                                                                              2))
        module_local_dir = os.path.dirname(__file__)
        im = Image.open(os.path.join(module_local_dir, population_map))
        self.arr = numpy.asarray(im)
        self.xlimit, self.ylimit = float(len(self.arr[0])), float(len(self.arr))
        # We used to normalise the pixels into floating point -
        # but explodes memory usage by x8!
        # Set area to choose from
        self.area = None

        logging.warning("Image size is " + str(self.arr.nbytes / (1024 * 1024)) + " MB")

    def set_area(self, area):
        """If <area> is defined it must be two strings: ["centre","edge"].
        Each string is an address (e.g. "Cambridge, UK") which is looked-up to get lat/lon.
        These are then used to define the centre and edge of an allowable circle to pick within"""
        # Pathologies:
        # . Asking for an area which contains zero population will spin forever
        # . Providing a huge map with a tiny populated area will be very slow
        # . The circle is a lon/lat circle. So on most map projections it will look circular over the equator,
        # but an increasingly vertical oval towards the poles (e.g. UK).
        self.area = area

        self.area_centre, self.area_edge = address_to_long_lat(area[0]), address_to_long_lat(area[1])

    def xy_to_lon_lat(self, (x, y)):
        # Normalise axes to +/-1
        y = (2 * y / self.ylimit) - 1.0
        x = (2 * x / self.xlimit) - 1.0

        # Longitude ranges from -180 degrees (East) to 180 degrees (West)
        # Latitude ranges from +90 degrees (North pole) to -90 degrees (South pole)

        longitude = x * 180.0
        latitude = y * -90.0  # (y goes down, latitude goes up)

        return longitude, latitude

    def lon_lat_to_x_y(self, (longitude, latitude)):
        # Reduce to +/-1
        x = longitude / 180.0
        y = latitude / -90.0

        x = ((x + 1.0) / 2.0) * self.xlimit
        y = ((y + 1.0) / 2.0) * self.ylimit

        x = max(min(x, self.xlimit), 0)
        y = max(min(y, self.ylimit), 0)

        return x, y

    def pick_point(self):
        """Returns a (latitude,longitude) point, on population map, within area"""

        global MINLONG, MAXLONG, MINLAT, MAXLAT, MINX, MAXX, MINY, MAXY

        while True:
            if self.area:
                radius = randint(0, int(self.areaRadiusPixels + 0.5))
                angle = random() * 2 * math.pi
                ox = math.sin(angle) * radius
                oy = math.cos(angle) * radius
                x = int(self.areaCentreXY[0] + ox)
                y = int(self.areaCentreXY[1] + oy)
            else:
                x, y = randint(0, self.xlimit - 1), randint(0,
                                                            self.ylimit - 1)  # Note: INTEGER pick, i.e nearest pixel.
            v = (self.arr[y][x] / 255.0)
            if v > random():
                break

        # Dither our pixels, otherwise all points will be on pixel grid
        x += random()
        y += random()

        longitude, latitude = self.xy_to_lon_lat((x, y))

        MINLAT = min(MINLAT, latitude)
        MAXLAT = max(MAXLAT, latitude)
        MINLONG = min(MINLONG, longitude)
        MAXLONG = max(MAXLONG, longitude)
        MINX = min(MINX, x)
        MAXX = max(MAXX, x)
        MINY = min(MINY, y)
        MAXY = max(MAXY, y)
        # print "x,y=",x,y," longitude,latitude=",longitude,latitude
        return longitude, latitude

    def pick_points(self, n=1):
        l = []
        for i in range(n):
            l.append(self.pick_point())
        return l


def main():
    p = PointPicker()
    p.pick_points(n=1000)  # , area=["London,UK","Cambridge,UK"])

    print "LONG:", MINLONG, MAXLONG, "DIFF", MAXLONG - MINLONG
    print "LAT:", MINLAT, MAXLAT, "DIFF", MAXLAT - MINLAT
    print "X:", MINX, MAXX, "DIFF", MAXX - MINX
    print "Y:", MINY, MAXY, "DIFF", MAXY - MINY


if __name__ == "__main__":
    main()
