import os
import appdirs


if appdirs.system == 'darwin':
    appname = 'hkOS'
else:
    appname = 'hkos'

CONFIG_DIR = os.environ.get(
    'HKOS_CONFIG_DIR',
    appdirs.user_config_dir(appname=appname)
)

DATA_DIR = os.environ.get(
    'HKOS_DATA_DIR',
    appdirs.user_data_dir(appname=appname)
)
