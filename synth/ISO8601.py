# ISO 8601 specifies a format for time which is a good tradeoff between machine-readable and human-readable
# It has optional separators.
# This module just turns a "seconds-since-the-Epoch" number into a valid string
# like "1995-02-04T13:11:00Z"
# The trailing "Z" means Zulu, i.e. UTC.
# Not declaring the timezone should be a capital offense!
#
# Interestingly, ISO8601 also supports intervals and even repeating intervals
# http://en.wikipedia.org/wiki/ISO_8601#Repeating_intervals
#
# Useful list of BST transitions here: http://wwp.greenwichmeantime.co.uk/info/bst2.htm
# NOTE: There were NO BST transitions in 1970/1971, as part of a UK "BST all year" experiment.
# The "fleming" open source library may also be helpful.
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
from datetime import datetime, timedelta, tzinfo
import pytz
import re


def make_timezone(tzname):
    # s is Olsen name of a timezone, e.g. "America/Los_Angeles"
    return pytz.timezone(tzname)


def epoch_seconds_to_datetime(secs, tz=pytz.utc):
    # get time in UTC
    utc_dt = datetime.utcfromtimestamp(secs).replace(tzinfo=pytz.utc)
    # convert it to tz
    return tz.normalize(utc_dt.astimezone(tz))


def epoch_seconds_to_iso8601(secs, tz=pytz.utc):
    return epoch_seconds_to_datetime(secs, tz).strftime('%Y-%m-%dT%H:%M:%S%z')


def to_epoch_seconds(iso8601, tz=pytz.utc):  # Default UTC timezone has no DST
    # (from pytz docs) Note: Unfortunately using the tzinfo argument of the standard datetime constructors does not
    # work with pytz for many timezones
    dt = parse_date(iso8601)
    tt = dt.timetuple()
    loc_dt = tz.localize(datetime(tt[0], tt[1], tt[2], tt[3], tt[4], tt[5], 00))
    epochsecs = (loc_dt - datetime(1970, 1, 1, 0, 0, 0, 0, pytz.utc)).total_seconds()

    return epochsecs


def yesterday_in_hours():
    t = time.time()
    (d, d, d, h, m, s, d, d, d) = time.gmtime(t)
    start = t - s - m * 60 - h * 60 * 60 - 86400  # Find start of previous whole day
    end = start + 86400
    start_s = epoch_seconds_to_iso8601(start)
    end_s = epoch_seconds_to_iso8601(end)
    return start_s, end_s, 3600


# Adapted from http://delete.me.uk/2005/03/iso8601.html
ISO8601_REGEX = re.compile(r"(?P<year>[0-9]{4})(-(?P<month>[0-9]{1,2})(-(?P<day>[0-9]{1,2})"
                           r"((?P<separator>.)(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2})"
                           r"(:(?P<second>[0-9]{2})(\.(?P<fraction>[0-9]+))?)?"
                           r"(?P<timezone>Z|(([-+])([0-9]{2}):([0-9]{2})))?)?)?)?"
                           )
TIMEZONE_REGEX = re.compile("(?P<prefix>[+-])(?P<hours>[0-9]{2}).(?P<minutes>[0-9]{2})")


class ParseError(Exception):
    """Raised when there is a problem parsing a date string"""


# Taken from python docs
ZERO = timedelta(0)


class Utc(tzinfo):
    """UTC
    
    """

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO


UTC = Utc()


class FixedOffset(tzinfo):
    """Fixed offset in hours and minutes from UTC
    
    """

    def __init__(self, offset_hours, offset_minutes, name, *args, **kwargs):
        super(FixedOffset, self).__init__(*args, **kwargs)
        self.__offset = timedelta(hours=offset_hours, minutes=offset_minutes)
        self.__name = name

    def utcoffset(self, dt):
        print "FixedOffset class utcoffset() returning", self.__offset
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

    def __repr__(self):
        return "<FixedOffset %r>" % self.__name


def parse_timezone(tzstring, default_timezone=UTC):
    """Parses ISO 8601 time zone specs into tzinfo offsets
    
    """

    if tzstring == "Z":
        return default_timezone
    # This isn't strictly correct, but it's common to encounter dates without
    # timezones so I'll assume the default (which defaults to UTC).
    # Addresses issue 4.
    if tzstring is None:
        return default_timezone
    m = TIMEZONE_REGEX.match(tzstring)
    prefix, hours, minutes = m.groups()
    hours, minutes = int(hours), int(minutes)
    if prefix == "-":
        hours = -hours
        minutes = -minutes
    return FixedOffset(hours, minutes, tzstring)


def parse_date(datestring, default_timezone=UTC):
    """Parses ISO 8601 dates into datetime objects
    
    The timezone is parsed from the date string. However it is quite common to
    have dates without a timezone (not strictly correct). In this case the
    default timezone specified in default_timezone is used. This is UTC by
    default.
    """
    if not isinstance(datestring, basestring):
        raise ParseError("Expecting a string %r" % datestring)
    m = ISO8601_REGEX.match(datestring)
    if not m:
        raise ParseError("Unable to parse date string %r" % datestring)
    groups = m.groupdict()
    tz = parse_timezone(groups["timezone"], default_timezone=default_timezone)
    if groups["fraction"] is None:
        groups["fraction"] = 0
    else:
        groups["fraction"] = int(float("0.%s" % groups["fraction"]) * 1e6)
    return datetime(int(groups["year"]), int(groups["month"]), int(groups["day"]),
                    int(groups["hour"]), int(groups["minute"]), int(groups["second"]),
                    int(groups["fraction"]), tz)


def self_test():
    # BST generally begins on the last Sunday in March
    # Note that there was no BST until 1972 because of a UK "BST all year" experiment!
    # Try 1972 - Sun 19th March was transition

    print "Testing DST"
    tz = make_timezone("Europe/London")  # Should work for any time zone, e.g. "America/New_York"

    for day in range(1, 31):
        today_str = "1972-03-%02dT00:00:00" % day
        today_secs = to_epoch_seconds(today_str, tz)

        tomorrow_str = "1972-03-%02dT00:00:00" % (day + 1)
        tomorrow_secs = to_epoch_seconds(tomorrow_str, tz)

        secs = int(tomorrow_secs - today_secs)
        print "Day " + epoch_seconds_to_iso8601(today_secs, tz) + " starts at " + str(today_secs) + " and contains " +\
              str(secs) + " seconds"

        if day != 19:
            assert secs == 24 * 60 * 60
        else:
            print "***FOUND DST event***"  # Detect DST start
            assert secs == 23 * 60 * 60

    print "Test passed"


if __name__ == "__main__":
    self_test()
