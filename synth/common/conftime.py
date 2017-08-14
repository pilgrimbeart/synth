import time
import isodate
import pendulum

def get_interval(conf, key, default):
    if key in conf:
        return pendulum.interval.instance(isodate.parse_duration(conf[key]))
    else:
        return default


def get_time(conf, key, default):
    if key in conf:
        return pendulum.interval.instance(isodate.parse_datetime(conf[key]))
    else:
        return default


def richTime(timeString):
    """Given human time string return epoch-seconds.

        Allowed formats:
        None (now)
        "now"
        "1980-04-01:00:00:00Z" (absolute time in ISO8601 format)
        "Px", "-Px" or "+Px" a time relative to now
           where x is an ISO8601 Duration https://en.wikipedia.org/wiki/ISO_8601
           (note that for periods < 1 day the T separator must be specified (resolves Months/Minutes ambiguity)
           e.g. "P1D"   a day from now
                "-P1D"  a day ago
                "PT1H"  an hour from now
                "+PT1H30M"" 90 minutes from now
                "-P1DT12H"  A day and a half ago"""
    if timeString==None:
        return time.time()
    elif timeString=="now":
        return time.time()
    elif timeString[0] in "-+P":
        return (pendulum.now() + isodate.parse_duration(timeString)).timestamp()
    else:
        return pendulum.parse(timeString).timestamp()
