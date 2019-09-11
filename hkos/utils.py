import configparser
from .paths import CONFIG_DIR


def load_config_file(name):
    cp = configparser.ConfigParser()

    cfgpath = "{configdir}/{name}.ini".format(
        configdir=CONFIG_DIR,
        name=name)

    with open(cfgpath, 'r', encoding='utf-8') as fh:
        cp.read_file(fh)

    return cp


def underscore_dict_keys(d, recurse=True):
    ret = {}
    for (k, v) in d.items():
        k = k.replace('-', '_')
        if isinstance(v, dict) and recurse:
            v = underscore_dict_keys(v, recurse=True)
        ret[k] = v

    return ret


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
