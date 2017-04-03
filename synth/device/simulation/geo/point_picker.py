#!/usr/bin/env python

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
from random import randint, random, seed

import numpy
from PIL import Image

Image.MAX_IMAGE_PIXELS = 1000000000  # We're dealing with large images, so prevent DecompressionBomb errors


class PointPicker:
    """Pick global coordinates that have statistics roughly matching technological population density.
    
    Population density is, by default, based on night-time light as a proxy.
     
    Data from:
        http://earthobservatory.nasa.gov/Features/NightLights/page3.php
    With the following manipuation: 
        1) "Enhance/Adjust Lighting/Levels" and set Blue channel to zero
        2) Convert to Greyscale
        3) Adjust Lighting and set black level to about 36 and white to 248, to eliminate sea/arctic and
            stretch to full-white

    The projection of this image maps the globe to fill a rectangle and is probably a "Plate-Carree" projection.
    
    Therefore the following projection translation function is used:
        latitude = y
        longitude = x / cos(latitude)

    """

    def __init__(self, population_map="population_map.jpg", random_seed=None):
        """Create a new instance for the point picker.
        
        Note that population density maps are often huge, so it is reccomended to maintain a singleton instance.
        
        Args:
            population_map (str, optional): Population density map, relative to module path.
            random_seed (float, optional): Seed for random number generation.
            
        Returns:
            PointPicker: Configured point picker.
        
        """
        seed(random_seed)

        self.restrict_to_area = False
        self.area_radius_pixels = 0.0
        self.area_centre_xy = [0.0, 0.0]

        module_local_dir = os.path.dirname(__file__)
        population_map_image = Image.open(os.path.join(module_local_dir, population_map))
        self.population_density = numpy.asarray(population_map_image)
        self.map_x_limit, self.map_y_limit = float(len(self.population_density[0])), float(len(self.population_density))

        logging.info("Image size is " + str(self.population_density.nbytes / (1024 * 1024)) + " MB")

    def set_area(self, area_centre=None, area_edge=None):
        """Restrains selected points to a given circular area.
        
        If both area_centre and area_edge are defined then the region of picked points is restrained.
        Note that:
            - Asking for an area which contains zero population will fall back to random selections.
            - Providing a huge map with a tiny populated area will be very slow and possibly result in random selection.
            - The circle is a lon/lat circle. So on most map projections it will look circular over the equator,
                but an increasingly vertical oval towards the poles (e.g. UK).
                
        Args:
            area_centre ((float, float), optional): Longitude/Latitude for the centre of area.
            area_edge ((float, float), optional): Longitude/Latitude for a point along the edge of the area.
            
        """
        if area_centre and area_edge:
            self.restrict_to_area = True
            self.area_centre_xy, area_edge_xy = self.lon_lat_to_xy(area_centre), self.lon_lat_to_xy(area_edge)
            self.area_radius_pixels = math.sqrt(
                math.pow(self.area_centre_xy[0] - area_edge_xy[0], 2) +
                math.pow(self.area_centre_xy[1] - area_edge_xy[1], 2))
        else:
            self.restrict_to_area = False

    def pick_points(self, count=1):
        """Returns a collection of random points within the popoulated area.
        
        Args:
            count (int, optional): Number of points to pick.
            
        Returns
            List[float, float]: List of longitude/latitudes of random points.
            
        """
        return [self.pick_point() for _ in range(count)]

    def pick_point(self):
        """Returns a (latitude,longitude) point, on population map, within a set area.
        
        Returns
            (float, float): Longitude/latitude of populated point.
            
        """
        x, y = 0.0, 0.0

        MAX_ITTERATIONS = 1000  # Protect against unpopulated areas causing infinite spin.
        for _ in range(MAX_ITTERATIONS):
            if self.restrict_to_area:
                radius = randint(0, int(self.area_radius_pixels + 0.5))
                angle = random() * 2 * math.pi
                ox = math.sin(angle) * radius
                oy = math.cos(angle) * radius
                x = int(self.area_centre_xy[0] + ox)
                y = int(self.area_centre_xy[1] + oy)
            else:
                x, y = randint(0, self.map_x_limit - 1), randint(0, self.map_y_limit - 1)
            p = (self.population_density[y][x] / 255.0)
            if p > random():
                break

        # Dither our pixels, otherwise all points will be on pixel grid
        x += random()
        y += random()

        return self.xy_to_lon_lat((x, y))

    def lon_lat_to_xy(self, (longitude, latitude)):
        """Convert a longitude/latitude tuple into a projection x/y.
        
        Args:
             (longitude, latitude) (float, float): Longitude, latitude point tuple.
            
        Returns
            (float, float): Image map x/y or extent. 
            
        """
        x = longitude / 180.0
        y = latitude / -90.0

        x = ((x + 1.0) / 2.0) * self.map_x_limit
        y = ((y + 1.0) / 2.0) * self.map_y_limit

        x = max(min(x, self.map_x_limit), 0)
        y = max(min(y, self.map_y_limit), 0)

        return x, y

    def xy_to_lon_lat(self, (x, y)):
        """Convert a projection x/y tuple into a longitude/latitude.

        Args:
             (x, y) ((float, float)): x, y point tuple

        Returns
            (float, float): longitude/latitude in degrees.

        """
        y = (2 * y / self.map_y_limit) - 1.0
        x = (2 * x / self.map_x_limit) - 1.0

        longitude = x * 180.0
        latitude = y * -90.0

        return longitude, latitude
