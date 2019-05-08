import importlib


def get_obj(spec):
    parts = spec.split('.')
    mod = '.'.join(parts[:-1])
    name = parts[-1]

    try:
        m = importlib.import_module(mod)
    except ModuleNotFoundError as e:
        raise LoadError(e.name) from e

    try:
        obj = getattr(m, name)
    except AttributeError as e:
        raise UnknowPluginError(spec) from e

    return obj


class RawLoader:
    def __init__(self):
        self.reg = {}

    def __iter__(self):
        yield from self.reg

    def register(self, name, target):
        if name in self.reg:
            raise DuplicatedTargetError(name)
        self.reg[name] = target

    def get(self, name):
        try:
            return self.reg[name]
        except KeyError as e:
            raise UnknownTargetError(name)

    def get_target_name(self, target):
        rev = {target: name for (name, target) in self.reg.items()}

        try:
            return rev[target]
        except KeyError as e:
            raise UnknownTargetError(cls) from e


class ClassLoader2(RawLoader):
    def __init__(self, basecls, lazy=Flase):
        self.basecls = basecls
        self.lazyloading = lazy

    def register(self, name, clsspec):
        if self.lazyloading:
            target = clsspec

        else:
            target = get_obj(clsname)
            if not isinstance(target, self.basecls):
                raise TypeError(target)

        super().register(name, target)

    def get(self, name):
        target = super().get(name)
        if self.lazyloading:
            return get_obj(target)
        else:
            return target


# class Loader:
#     def __init__(self, cls=object):
#         self.basecls = cls
#         self.reg = {}

#     def register(self, name, spec):
#         try:
#             cls = get_obj(spec)
#         except ModuleNotFoundError as e:
#             raise LoadError(e.name) from e
#         except AttributeError as e:
#             raise UnknowPluginError(spec) from e


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
