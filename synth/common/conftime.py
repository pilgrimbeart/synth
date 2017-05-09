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
