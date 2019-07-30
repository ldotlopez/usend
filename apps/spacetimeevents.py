import hkos.utils


import collections
import datetime
import math
import time


import croniter


EARTH_RADIUS = 6_371_000


class App:
    def __init__(self, rules):
        self.rules = rules

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

        for (name, rule) in self.rules.items():
            if rule.match(location=where, time=when):
                print(name)


class Location:
    def __init__(self, latitude, longitude):
        if not all([
                isinstance(x, (float, int))
                for x in (latitude, longitude)]):
            raise ValueError("latitude and longitude must be floats")

        self.latitude = latitude
        self.longitude = longitude

    @classmethod
    def fromstring(cls, s):
        lat, lng = s.split(',')
        lat = float(lat)
        lng = float(lng)

        return cls(lat, lng)

    def __repr__(self):
        return 'Location(%f, %f)' % (self.latitude, self.longitude)

    def haversine(self, other):
        lon1, lat1, lon2, lat2 = map(
            math.radians,
            [self.longitude, self.latitude, other.longitude, other.latitude])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = (math.sin(dlat / 2)**2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        meters = EARTH_RADIUS * c

        return meters

    def equirectangular(self, other):
        lon1, lat1, lon2, lat2 = map(
            math.radians,
            [self.longitude, self.latitude, other.longitude, other.latitude])

        x = (lon2 - lon1) * math.cos(0.5*(lat2+lat1))
        y = lat2 - lat1
        d = EARTH_RADIUS * math.sqrt(x**2 + y**2)

        return d


class Rule:
    def __init__(self,
                 time_start=None, time_end=None,
                 location=None, location_radius=100):
        if not time_start and not location:
            raise ValueError("time_start or location required")

        if location and not isinstance(location, Location):
            raise TypeError("location must be a Location")

        self.time_start = time_start
        self.time_end = time_end
        self.location = location
        self.location_radius = location_radius

    def __repr__(self):
        retstr = ("Rule(time_start=%r, time_end=%r, "
                  "location=%r, location_radius=%d meters')")
        return retstr % (self.time_start, self.time_end,
                         self.location, self.location_radius)

    def match(self, location=None, time=None):
        def match_location():
            if not location:
                return True

            distance = self.location.equirectangular(location)
            return (distance <= self.location_radius)

        def match_time():
            if not time:
                return True

            if not (self.time_start and self.time_end):
                excmsg = ("rules without both start and end time are not "
                          "supported")
                raise NotImplementedError(excmsg)

            it1 = croniter.croniter(self.time_start, time)
            it2 = croniter.croniter(self.time_end, time)
            dt_start = datetime.datetime.fromtimestamp(it1.get_next())
            dt_end = datetime.datetime.fromtimestamp(it2.get_next())

            return dt_start > dt_end

        if not location and not time:
            raise ValueError("location or time requiered")

        return match_time() and match_location()


def load_config(filepath=None):
    if filepath is None:
        cp = hkos.utils.load_config_file('spacetimeevents')
    else:
        with open(filepath, 'r', encoding='utf-8') as fh:
            cp.read_file(fh)

    cfg = {sect: dict(cp[sect].items())
           for sect in cp.sections()}

    rules = {}
    for (name, params) in cfg.items():

        if 'location' in params:
            params['location'] = Location.fromstring(params['location'])

        if 'location-radius' in params:
            params['location-radius'] = float(params['location-radius'])

        params = {k.replace('-', '_'): v for (k, v) in params.items()}
        rules[name] = Rule(**params)

    return {
        'rules': rules
    }


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

    where = Location.fromstring(args.space) if args.space else None
    when = hkos.utils.parse_time(args.time) if args.time else None

    config = load_config()

    app = App(rules=config['rules'])
    app.run(where, when)


if __name__ == '__main__':
    main()
