#!/usr/bin/env python

# Utility solar functions (with no side-effects)
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

import time
from math import sin, pi

from synth.devices.blb_helpers.sun_position import sun_position


def sun_angle(epoch_secs, (longitude, latitude)):
    """Returns the angle of the sun at a given time.

    Args:
        epoch_secs (int): Seconds since the ISO8601 epoch.
        (longtiude, latitude) (float, float): Longitude/Latitude pair to calculate sun angle at.

    Returns:
        (float, float): azimuth and elevation.
    """
    at = time.gmtime(epoch_secs)
    (azimuth, elevation) = sun_position(at.tm_year, at.tm_mon, at.tm_mday, at.tm_hour, at.tm_min,
                                         at.tm_sec, latitude, longitude)
    return azimuth, elevation


def sun_bright(epoch_secs, (longitude, latitude)):
    """Returns the sun's brightness at a given time.

    Args:
        epoch_secs (int): Seconds since the ISO8601 epoch.
        (longtiude, latitude) (float, float): Longitude/Latitude pair to calculate sun angle at.

    Returns:
        float: Brigtness.
    """
    az_d, elev_d = sun_angle(epoch_secs, (longitude, latitude))
    elev_r = 2 * pi * (elev_d / 360.0)
    bright = max(0.0, sin(elev_r))
    return bright
