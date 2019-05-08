import importlib


class ClassLoader:
    def __init__(self, cls=object):
        self.basecls = cls
        self.reg = {}

    def register(self, name, objstr):
        if name in self.reg:
            raise DuplicatedPluginError(name)

        self.reg[name] = objstr

    def __iter__(self):
        yield from self.reg

    def get(self, name):
        try:
            objstr = self.reg[name]
        except KeyError as e:
            raise UnknowPluginError(name)

        parts = objstr.split('.')
        mod = '.'.join(parts[:-1])
        cls = parts[-1]

        try:
            m = importlib.import_module(mod)
        except ModuleNotFoundError as e:
            raise LoadError(e.name) from e

        try:
            cls = getattr(m, cls)
        except AttributeError as e:
            raise UnknowPluginError(objstr) from e

        if not issubclass(cls, self.basecls):
            raise TypeError(cls)

        return cls

    # def get_class_name(self, cls):
    #     cls_full_name = cls.__module__ + '.' + cls.__name__
    #     m = {clsname: pubname for (pubname, clsname) in self.reg.items()}

    #     try:
    #         return m[cls_full_name]
    #     except KeyError as e:
    #         raise UnknowPluginError(cls) from e


class LoadError(Exception):
    pass


class DuplicatedPluginError(Exception):
    pass


class UnknowPluginError(Exception):
    pass
