import isodate
import pendulum

def get_interval(conf, key, default):
    return pendulum.interval.instance(isodate.parse_duration(conf[key])) if key in conf else default

def get_time(conf, key, default):
    return pendulum.instance(isodate.parse_datetime(conf[key])) if key in conf else default
