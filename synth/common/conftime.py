import isodate
import pendulum

def get_interval(conf, key, default):
    return pendulum.interval.instance(
        isodate.parse_duration(
           conf.get(key, default)
        )
    )
