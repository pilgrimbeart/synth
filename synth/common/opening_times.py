# Opening times as specified by https://schema.org/openingHours
# (with the exception that multiple specifications within a string are separated by ";")
# This is the opening-hours format that DevicePilot uses
#
# Copyright (c) 2020 DevicePilot Ltd.
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

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
RANGE_SEP = "-"

def starts_with_day(s):
    for d in range(len(DAYS)):
        if s.startswith(DAYS[d]):
            return d
    return None

class Spec():
    def __init__(self):
        self.days = [False] * len(DAYS)
        self.start_hour = 0
        self.end_hour = 24

    def add_day(self, dayNum):
        self.days[dayNum] = True

    def is_valid(self):
        # At least one day defined
        day_defined = False
        for d in self.days:
            day_defined = day_defined or d
        if not day_defined:
            return False

        if self.start_hour > 24:
            return False
        if self.end_hour > 24:
            return False

        return True

    def is_within(self, dayNum, hours):
        if self.days[dayNum] == True:
            if hours >= self.start_hour:
                if hours <= self.end_hour:
                    return True
        return False

    def __repr__(self):
        days = []
        for d in range(len(DAYS)):
            if self.days[d]:
                days.append(DAYS[d])
        days = ",".join(days)

        start_hour = "%02d:%02d" % (int(self.start_hour), int((self.start_hour - int(self.start_hour)) * 60)) 
        end_hour = "%02d:%02d" % (int(self.end_hour), int((self.end_hour - int(self.end_hour)) * 60)) 
        hours = start_hour + RANGE_SEP + end_hour

        return days + " " + hours

def _parse_opening_time(specstr):
    spec = Spec()

    if " " in specstr:
        day_spec, time_spec = specstr.split(" ")
    else:
        day_spec = specstr
        time_spec = None

    while day_spec != "":
        # Parse day(s)
        day = starts_with_day(day_spec)
        assert day is not None, day_spec + " missing day"
        day_spec = day_spec[2:]

        if day_spec.startswith(RANGE_SEP):
            end_day = starts_with_day(day_spec[1:])
            assert end_day is not None, day_spec + " missing end day"
            day_spec = day_spec[3:]
        else:
            end_day = day

        for d in range(day, end_day+1):
            spec.add_day(d)

        if day_spec.startswith(","):
            day_spec = day_spec[1:]

    # Parse time range
    if time_spec is not None:
        assert len(time_spec)==11 and time_spec[2]==":" and time_spec[5]=="-" and time_spec[8]==":", time_spec + " time specification must be 24-hour range exactly as NN:NN-NN:NN"
        spec.start_hour = int(time_spec[0:2]) + int(time_spec[3:5])/60.0
        spec.end_hour = int(time_spec[6:8]) + int(time_spec[9:11])/60.0
        assert spec.is_valid(), time_spec + " specification invalid"

    return spec


def parse(desc):
    specs = [] 
    for spec in desc.split(";"):
        spec = spec.strip()
        specs.append(_parse_opening_time(spec))
    return specs

def is_open(epoch, specs):
    """Given a list of spec classes (as returned by parse_opening_times),
       returns true if the time (in Unix epoch-seconds) is within the specified range"""
    t = time.gmtime(epoch)
    weekday = t.tm_wday  # Monday is 0, same as we use here
    hour = t.tm_hour + t.tm_min/60.0 + t.tm_sec/3600.0

    for spec in specs:
        if spec.is_within(weekday, hour):
            return True

    return False

tests = [
    ("Mo-Mo", "[Mo 00:00-24:00]"),
    ("Mo-Tu", "[Mo,Tu 00:00-24:00]"),
    ("Mo-Su", "[Mo,Tu,We,Th,Fr,Sa,Su 00:00-24:00]"),
    ("Mo 09:00-12:00", "[Mo 09:00-12:00]"),
    ("Mo,Tu,We,Th,Fr 01:23-23:45", "[Mo,Tu,We,Th,Fr 01:23-23:45]"),
    ("Mo-Fr 09:00-17:00", "[Mo,Tu,We,Th,Fr 09:00-17:00]"),
    ("Mo-Th,Sa 09:00-17:00", "[Mo,Tu,We,Th,Sa 09:00-17:00]"),
    ("Mo-Fr 09:00-17:00; Sa 10:00-12:00","[Mo,Tu,We,Th,Fr 09:00-17:00, Sa 10:00-12:00]"),
    ("Mo-Xa", "ASSERT"),
    ("Xa-Mo", "ASSERT"),
    ("Mo-Fr 09:00", "ASSERT"),
    ("Mo-Fr 09:00-", "ASSERT"),
    ("Mo-Fr 09:00-1", "ASSERT"),
    ("Mo-Fr 09:00-25:00", "ASSERT")
        ]

def selfTest():
    import sys, traceback

    for test, expected in tests:
        print(test+" ", end="")
        try:
            result = repr(parse(test))
            print("->",result, end="")
            assert result==expected, "FAILED: Expected " + expected
            print(" OK")
        except:
            if expected != "ASSERT":
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print()
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
                sys.exit()
            else:
                print(" ASSERTED AS EXPECTED")
    print("PARSING TESTS PASSED")

if __name__ == "__main__":
    selfTest()
