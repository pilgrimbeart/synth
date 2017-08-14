#!/usr/bin/env python
#
# WIND
# Utility wind functions (with no side-effects).
# Main goal is plausible, repeatable randomness without state
# (i.e. given any moment in time, return wind at that time)
# so works well with simulators that might have any tick interval
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

# Set of frequencies to simulate bursty wind
diurnalPeriods = [ (42, 1),
                   (66, 1),
                   (102,1),
                   (126,1),
                   (60*60*12,1) ]

seasonalPeriods = [ (60*60*24*4,    1), # Synoptic
                    (60*60*24*5.7,  1),
                    (60*60*24*9.7,  1),
                    (60*60*24*29,   2), # Monthly
                    (60*60*24*40,   2),
                    (60*60*24*30*6, 2),
                    (60*60*24*30*6.1, 2) ]


def sinSum(epochSecs, table):
    value = 0.0
    ampSum = 0.0
    for (period, amplitude) in table:
        value += sin(epochSecs * 2 * pi / period) * amplitude
        ampSum += amplitude
    return value / ampSum

def windStrength(epochSecs):
    """Returns signed value -1.0..1.0."""
    diurnal = sinSum(epochSecs, diurnalPeriods)
    seasonal = sinSum(epochSecs, seasonalPeriods)
    return diurnal * seasonal

if __name__ == "__main__":
    for i in range(0,1000):
        print windStrength(i*300)
