import configparser
from .paths import CONFIG_DIR
from .beacon import Beacon


def load_config_file(name):
    cp = configparser.ConfigParser()

    cfgpath = "{configdir}/{name}.ini".format(
        configdir=CONFIG_DIR,
        name=name)

    with open(cfgpath, 'r', encoding='utf-8') as fh:
        cp.read_file(fh)

    return cp


__all__ = [
    'Beacon',
    'load_config_file'
]
