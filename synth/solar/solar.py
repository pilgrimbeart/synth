#!/usr/bin/env python
#
# SOLAR
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

from math import sin, pi

import sunpos_2
from synth import ISO8601


def second_of_day(epoch_secs):
    s = ISO8601.epoch_seconds_to_iso8601(epoch_secs)
    s = "1970-01-01" + s[10:]
    return ISO8601.to_epoch_seconds(s)


def diurnal_cycle(epoch_secs):
    # Varies from 0 at midnight to 1 at midday and back again
    e = second_of_day(epoch_secs)
    frac = e / float(days(1))  # Fraction of a day
    return 0.5 + sin(3 * pi / 2 + frac * pi * 2) / 2


def sun_angle(epoch_secs, (longitude, latitude)):
    date_s = ISO8601.epoch_seconds_to_iso8601(epoch_secs)
    year = int(date_s[0:4])
    month = int(date_s[5:7])
    day = int(date_s[8:10])
    hour = int(date_s[11:13])
    minute = int(date_s[14:16])
    sec = int(date_s[17:19])
    (azimuthD, elevationD) = sunpos_2.sun_position(year, month, day, hour, minute, sec, latitude, longitude)
    return azimuthD, elevationD


def sun_bright(epoch_secs, (longitude, latitude)):
    az_d, elev_d = sun_angle(epoch_secs, (longitude, latitude))
    elev_r = 2 * pi * (elev_d / 360.0)
    bright = max(0.0, sin(elev_r))
    return bright


if __name__ == "__main__":
    import random

    elevMin = 1000000
    elevMax = -1000000
    for i in range(1000):
        longitude = random.random() * 360 - 180.0
        latitude = random.random() * 180 - 9.0
        t = int(random.random() * 60 * 60 * 24 * 365 * 50)
        print longitude, latitude, t
        azD, elevD = sun_bright(t, (longitude, latitude))
        print "shit"
        elevR = 2 * pi * (elevD / 360.0)
        print longitude, latitude, azD, elevD, sin(elevR)
        elevMin = min(elevMin, elevD)
        elevMax = max(elevMax, elevD)
    print "Min/Max elev:", elevMin, elevMax
