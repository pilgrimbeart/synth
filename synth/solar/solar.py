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


def secondOfDay(epochSecs):
    s = ISO8601.epochSecondsToISO8601(epochSecs)
    s = "1970-01-01" + s[10:]
    return ISO8601.toEpochSeconds(s)    

def diurnalCycle(epochSecs):
    # Varies from 0 at midnight to 1 at midday and back again
    e = secondOfDay(epochSecs)
    frac = e / float(days(1))  # Fraction of a day
    return 0.5 + sin(3*pi/2 + frac*pi*2)/2

def sunAngle(epochSecs, (longitude, latitude)):
    dateS = ISO8601.epochSecondsToISO8601(epochSecs)
    year = int(dateS[0:4])
    month = int(dateS[5:7])
    day = int(dateS[8:10])
    hour = int(dateS[11:13])
    minute = int(dateS[14:16])
    sec = int(dateS[17:19])
    (azimuthD, elevationD) = sunpos_2.sun_position(year, month, day, hour, minute, sec, latitude, longitude)
    return azimuthD, elevationD

def sunBright(epochSecs, (longitude, latitude)):
    azD,elevD = sunAngle(epochSecs, (longitude, latitude))
    elevR = 2*pi*(elevD/360.0)
    bright = max(0.0, sin(elevR))
    return bright

if __name__ == "__main__":
    import random
    elevMin=1000000
    elevMax=-1000000
    for i in range(1000):
        longitude = random.random()*360-180.0
        latitude = random.random()*180-9.0
        t = int(random.random()*60*60*24*365*50)
        print longitude, latitude, t
        azD,elevD = sunBright(t, (longitude, latitude))
        print "shit"
        elevR = 2*pi*(elevD/360.0)
        print longitude, latitude, azD,elevD, sin(elevR)
        elevMin = min(elevMin, elevD)
        elevMax = max(elevMax, elevD)
    print "Min/Max elev:",elevMin, elevMax
