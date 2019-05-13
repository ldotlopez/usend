import hkos.utils

import datetime
import time
from math import radians, cos, sin, asin, sqrt

import croniter
import collections


class App():
    def __init__(self, events):
        self.events = events

    def run(self, where, when):
        if when is None:
            when = time.mktime(time.localtime())

        if isinstance(when, (int, float)):
            when = datetime.datetime.fromtimestamp(when)
            when = when.astimezone()
        elif isinstance(when, datetime.datetime):
            if when.tzinfo is None:
                when = when.astimezone()
        else:
            raise TypeError(when)

        for (name, params) in self.events.items():
            it1 = croniter.croniter(params['time-start'], when)
            it2 = croniter.croniter(params['time-end'], when)
            dt_start = datetime.datetime.fromtimestamp(it1.get_next())
            dt_end = datetime.datetime.fromtimestamp(it2.get_next())

            if dt_start > dt_end:
                print(name)


_Location = collections.namedtuple(
    '_Location',
    ['latitude', 'longitude'])


class Location(_Location):
    def __new__(cls, latitude, longitude):
        if not all([
                isinstance(x, (float, int))
                for x in (latitude, longitude)]):
            raise ValueError("latitude and longitude")


_Rule = collections.namedtuple(
    '_Rule',
    ['time_start', 'time_end', 'location', 'location_radius']
)


class Rule(_Rule):
    def __new__(cls, time_start=None, time_end=None,
                location=None, location_radius=None):
        if not time_start and not location:
            raise ValueError("time_start or location required")

        if not (
                isinstance(location, (list, tuple))
                and len(location) == 2):
            raise TypeError("location must be a tuple or list")

        return super().__new__(cls, time_start, time_end, location,
                               location_radius)

    def match(self, location=None, time=None):
        def match_location():
            if not location:
                return True

            return (equirectangular(self.location, location)
                    <= self.location_radius)

        def match_time():
            if not time:
                return True

        if not location and not time:
            raise ValueError("location or time requiered")

        return match_time() and match_location()


def match(latlng, time, rulespec):
    it1 = croniter.croniter(rulespec['time-start'], time)
    it2 = croniter.croniter(rulespec['time-end'], time)
    dt_start = datetime.datetime.fromtimestamp(it1.get_next())
    dt_end = datetime.datetime.fromtimestamp(it2.get_next())

    dist = equirectangular(latlng, rulespec['space-point'])

    return dt_start > dt_end and dist <= rulespec['space-radius']


def haversine(p1, p2):
    lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    meters = 6_371_000 * c
    return meters


def equirectangular(p1, p2):
    lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])

    R = 6_371_100
    x = (lon2 - lon1) * cos(0.5*(lat2+lat1))
    y = lat2 - lat1
    d = R * sqrt(x**2 + y**2)

    return d


def load_config():
    cp = hkos.utils.load_config_file('spacetime-events')
    return {sect: dict(cp[sect].items())
            for sect in cp.sections()}


def parse_spacetime(reqstr):
    if '@' in reqstr:
        geostr, timestr = reqstr.split('@', 1)
    else:
        geostr, timestr = '40,0', reqstr

    return parse_geo(geostr), parse_time(timestr)


def parse_geo(geostr):
    lat, lng = geostr.split(',')
    lat = float(lat)
    lng = float(lng)

    return lat, lng


def parse_time(timestr, base_dt=None):
    if base_dt is None:
        base_dt = datetime.datetime.now()
        base_dt = base_dt.astimezone()

    dt_formats = [
        ('%Y-%m-%d %H:%M:%S',
         ['year', 'month', 'day', 'hour', 'minute', 'second']),
        ('%Y-%m-%d %H:%M',
         ['year', 'month', 'day', 'hour', 'minute']),
        ('%H:%M:%S',
         ['hour', 'minute', 'second']),
        ('%H:%M',
         ['hour', 'minute']),
    ]

    if not timestr:
        return base_dt

    for (fmt, fields) in dt_formats:
        try:
            dt = datetime.datetime.strptime(timestr, fmt)
            repls = {f: getattr(dt, f) for f in fields}
            return base_dt.replace(**repls)

        except ValueError:
            pass

    raise ValueError(timestr)


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--time',
        default=None,
    )
    parser.add_argument(
        '--space',
        default=None,
    )
    args = parser.parse_args(sys.argv[1:])

    where = parse_time(args.space) if args.space else None
    when = parse_time(args.time) if args.time else None

    app = App(events=load_config())
    app.run(where, when)


if __name__ == '__main__':
    main()
