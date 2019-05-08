#!/usr/bin/env python3

import argparse
import configparser
import os
import sys


from hkos.blocks import classloader
from hkos.blocks import usend


def load_profile(config, profile_name):
    """
    FIXME: generalize and move to core module
    """
    ret = {}
    if not config.has_section(profile_name):
        raise KeyError(profile_name)

    for (name, value) in config.items(profile_name):
        ret[name] = value

    try:
        includes = re.split(r"[\s,]+", ret.pop('!include'))
    except KeyError:
        return ret

    for x in includes:
        ret.update(load_profile(config, x))

    return ret


def load_config_files(config_files):
    config = configparser.ConfigParser()

    for config_file in config_files:
        try:
            with open(config_file, 'r', encoding='utf-8') as fh:
                config.read_file(fh)
            break

        except OSError as e:
            errmsg = "Can't read config file '{filepath}': {msg}"
            errmsg = errmsg.format(filepath=config_file, msg=str(e))
            print(errmsg, file=sys.stderr)

    return config


# def build_transport(cls_or_name, params):
#     if isinstance(cls_or_name, str):
#         cls = transport_for_name(cls_or_name)
#     elif isinstance(cls_or_name, Transport):
#         cls = cls_or_name
#     elif cls_or_name is None:
#         cls = transport_for_name(params.pop('backend'))
#     else:
#         raise TypeError(cls_or_name,
#                         'Transport class, string or None required')

#     if not isinstance(params, dict):
#         raise TypeError(params, 'dict required')

#     # Extract Transport.__init__ params
#     init_params = {}
#     remaining = {}

#     for (k, v) in params.items():
#         if k.startswith(cls.NAME + '_'):
#             k = k[len(cls.NAME) + 1:]
#             init_params[k] = v
#         else:
#             remaining[k] = v

#     transport = cls(**init_params)

#     return transport, remaining


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--transport',
        default='',
        dest='transport_name',
        help='Transport to use.'
    )
    parser.add_argument(
        '-c', '--conf',
        default='',
        dest='config_file',
        help='Use config file.'
    )
    parser.add_argument(
        '--profile',
        dest='profile_name',
        default='',
    )
    parser.add_argument(
        '--help',
        dest='help',
        action='store_true'
    )
    args, remaining = parser.parse_known_args(sys.argv[1:])

    # Read config
    default_config_files = [
        os.path.expanduser('~/.config/usend.ini'),
        os.path.expanduser('~/.usend.ini')
    ]
    if args.config_file:
        config = load_config_files([args.config_file])
    else:
        config = load_config_files(default_config_files)

    # Load profile if defined
    if args.profile_name:
        profile = load_profile(config, args.profile_name)
    else:
        profile = {}

    # Get transport
    transport_name = (
        args.transport_name or
        profile.get('transport', None)
        or ''
    )
    if not transport_name:
        parser.print_help()
        print("Transport param is required", file=sys.stderr)
        sys.exit(1)

    # Rebuild parser
    loader = usend.USendLoader.get_default()
    transport_cls = loader.get(transport_name)
    transport_cls.configure_argparser(parser)

    # --help support
    args = parser.parse_args(sys.argv[1:])
    if args.help:
        parser.print_help()
        sys.exit(1)

    # Cleanup params
    params = vars(args)
    for k in ['config_file', 'profile_name', 'transport_name', 'help']:
        params.pop(k, None)

    init_params, send_params = usend.split_params(transport_cls, params)
    transport = transport_cls(**init_params)

    try:
        transport.send(**send_params)
    except usend.SendError as e:
        msg = "Send failed: {err}"
        msg = msg.format(err=str(e))
        print(msg, file=sys.stderr)


if __name__ == '__main__':
    main()
