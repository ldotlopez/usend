from glob import fnmatch


class Router(dict):
    def match(self, key):
        try:
            return self[key]
        except KeyError:
            pass

        routes = sorted(self.items(),
                        key=lambda x: len(x[0]),
                        reverse=True)
        for (pattern, value) in routes:
            if fnmatch.fnmatch(key, pattern):
                return value

        raise NoRouteException(key)


class NoRouteException(Exception):
    def __init__(self, key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = key
