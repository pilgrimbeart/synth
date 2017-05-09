#!/usr/python
# coding=utf-8

# Copyright https://github.com/Neon22/sun-angle [MIT license]
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

import math


def is_leapyear(year):
    """Returns true if year was a leapyear."""
    if year % 400 == 0:
        return True
    elif year % 100 == 0:
        return False
    elif year % 4 == 0:
        return True
    else:
        return False


def to_sun_time(year, month, day, hour=12, minute=0, sec=0):
    """Returns the caluclation time from individual year/month/day/hour/minute/second arguments."""
    # Get day of the year, e.g. Feb 1 = 32, Mar 1 = 61 on leap years
    month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30]
    day = day + sum(month_days[:month])
    leapdays = is_leapyear(year) and day >= 60 and (not (month == 2 and day == 60))
    if leapdays:
        day += 1
    # Get Julian date - 2400000
    hour = hour + minute / 60.0 + sec / 3600.0  # hour plus fraction
    delta = year - 1949
    leap = delta // 4  # former leapyears
    jd = 32916.5 + delta * 365 + leap + day + hour / 24.0
    # The input to the Astronomer's almanac is the difference between the Julian date and JD 2451545 (12:00 01/01/2000)
    time = jd - 51545
    return time


def mean_longitude_degrees(time):
    """Returns mean longitude (in degrees) at time."""
    return (280.460 + 0.9856474 * time) % 360


def mean_anomaly_radians(time):
    """Returns mean anomaly (in radians) at time."""
    return math.radians((357.528 + 0.9856003 * time) % 360)


def ecliptic_longitude_radians(mnlong, mnanomaly):
    """Returns ecliptic longitude radians from mean longitude and anomaly correction."""
    return math.radians((mnlong + 1.915 * math.sin(mnanomaly) + 0.020 * math.sin(2 * mnanomaly)) % 360)


def ecliptic_obliquity_radians(time):
    """Returns ecliptic obliquity radians at time."""
    return math.radians(23.439 - 0.0000004 * time)


def right_ascension_radians(oblqec, eclong):
    """Returns assention from right in radians from obliquity and ecliptic longitude radians."""
    num = math.cos(oblqec) * math.sin(eclong)
    den = math.cos(eclong)
    ra = math.atan(num / den)
    if den < 0:
        ra += math.pi
    if den >= 0.0 and den > num:
        ra += 2 * math.pi
    return ra


def right_declination_radians(oblqec, eclong):
    """Returns declination from right in radians from obliquity and ecliptic longitude radians."""
    return math.asin(math.sin(oblqec) * math.sin(eclong))


def greenwich_mean_sidereal_time_hours(time, hour):
    """Returns GMT hours from time hours."""
    return (6.697375 + 0.0657098242 * time + hour) % 24


def local_mean_sidereal_time_radians(gmst, longitude):
    """Returns local hours from time hours and longitude."""
    return math.radians(15 * ((gmst + longitude / 15.0) % 24))


def hour_angle_radians(lmst, ra):
    """Returns hour angle radians from local time and right ascention."""
    return ((lmst - ra + math.pi) % (2 * math.pi)) - math.pi


def elevation_radians(lat, dec, ha):
    """Returns elevation radians."""
    return math.asin(math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha))


def solar_azimuth_radians_charlie(lat, dec, ha):
    """Returns azimuth charlie."""
    zenithAngle = math.acos(math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha))
    _az = math.acos((math.sin(lat) * math.cos(zenithAngle) - math.sin(dec)) / (math.cos(lat) * math.sin(zenithAngle)))
    if ha > 0:
        _az = _az + math.pi
    else:
        _az = (3 * math.pi - _az) % (2 * math.pi)
    return _az


def sun_position(year, month, day, hour=12, minute=0, sec=0, latitude=46.5, longitude=6.5):
    """Return the sun position at a given date time.

    Taken from the code on stackexchange here:
        - http://stackoverflow.com/questions/8708048/position-of-the-sun-given-time-of-day-latitude-and-longitude
        converted into Python and extensively tested.

    Args:
        year (int): Year
        month (int): Month
        day (int): Day
        hour (int): Hour
        minute (int): Minute
        sec (int): Second
        latitude (float): Latitude, as defined by +-90 degrees where 0 is the equator and +90 is the North Pole.
        longitude (float): Longitude is +- 180 degrees about the GMT line, where +ve values lie to the East.

    Returns:
        float, float: Azimuth and elevation.

"""
    time = to_sun_time(year, month, day, hour, minute, sec)
    hour = hour + minute / 60.0 + sec / 3600.0
    # Ecliptic coordinates
    mnlong = mean_longitude_degrees(time)
    mnanom = mean_anomaly_radians(time)
    eclong = ecliptic_longitude_radians(mnlong, mnanom)
    oblqec = ecliptic_obliquity_radians(time)
    # Celestial coordinates
    ra = right_ascension_radians(oblqec, eclong)
    dec = right_declination_radians(oblqec, eclong)
    # Local coordinates
    gmst = greenwich_mean_sidereal_time_hours(time, hour)
    lmst = local_mean_sidereal_time_radians(gmst, longitude)
    # Hour angle
    ha = hour_angle_radians(lmst, ra)
    # Latitude to radians
    latitude = math.radians(latitude)
    # Azimuth and elevation
    elevation = elevation_radians(latitude, dec, ha)
    # azJ = solarAzimuthRadiansJosh(lat, dec, ha, el)
    azC = solar_azimuth_radians_charlie(latitude, dec, ha)

    elevation = math.degrees(elevation)
    azimuth = math.degrees(azC)
    return azimuth, elevation
