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
