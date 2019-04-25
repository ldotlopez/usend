class Beacon:
    EVENTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handlers = {name: set() for name in self.EVENTS}

    def emit(self, name, **kwargs):
        for (fn) in self._handlers[name]:
            fn(self, **kwargs)

    def watch(self, name, fn):
        self._handlers[name].add(fn)

    def unwatch(self, name, fn):
        self._handlers[name].remove(fn)
