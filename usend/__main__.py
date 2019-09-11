#!/usr/bin/env python3

import argparse
import configparser
import os
import re
import sys


import usend


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


def load_config_files(*config_files):
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
        config = load_config_files(*args.config_file)
    else:
        config = load_config_files(*default_config_files)

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
    transport_cls = usend.get_transport(transport_name)
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

    init_params, send_params = usend.split_params(transport_cls, **params)
    transport = transport_cls(**init_params)

    try:
        transport.send(**send_params)
    except usend.SendError as e:
        msg = "Send failed: {err}"
        msg = msg.format(err=str(e))
        print(msg, file=sys.stderr)


def load_config_files2(*config_filepaths):
    config = configparser.ConfigParser()

    for filepath in config_filepaths:
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                config.read_file(fh)
            break

        except OSError as e:
            errmsg = "Can't read config file '{filepath}': {msg}"
            errmsg = errmsg.format(filepath=filepath, msg=str(e))
            print(errmsg, file=sys.stderr)

    return {
        sect: {
            k.replace('-', '_'): v
            for (k, v)
            in config[sect].items()
        }
        for sect
        in config
        if sect != 'DEFAULT'
    }


def get_basic_argument_parser():
    parser = argparse.ArgumentParser(add_help=False)
    basic = parser.add_argument_group('Basic arguments')
    basic.add_argument(
        '-h', '--help',
        action='store_true')
    basic.add_argument(
        '-c', '--config',
        default=[
            os.path.expanduser('~/.config/usend.ini'),
            os.path.expanduser('~/.usend.ini')
        ],
        action='append',
        required=False)

    mode_group = basic.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--transport',
        required=False)
    mode_group.add_argument(
        '--profile',
        required=False)

    return parser


def get_full_argument_parser(transport):
    parser = get_basic_argument_parser()
    configure_argparser_for_transport(parser, transport)

    return parser


def configure_argparser_for_transport(parser, transport):
    cls = usend.get_transport(transport)

    transport_group = parser.add_argument_group('Transport arguments')
    for param in cls.PARAMETERS:
        args = (
            '--' + cls.name() + '-' + param.name.replace('_', '-'),
        )
        kwargs = {
            'required': param.required,
            'type': param.type
        }
        if not param.required:
            kwargs['default'] = param.default
        transport_group.add_argument(*args, **kwargs)

    send_group = parser.add_argument_group('Send arguments')
    if cls.CAPS & usend.Capability.RECIEVER:
        send_group.add_argument(
            '-t', '--to',
            dest='destination',
        )

    if cls.CAPS & usend.Capability.MESSAGE:
        send_group.add_argument(
            '--message',
            dest='message',
        )

    if cls.CAPS & usend.Capability.DETAILS:
        send_group.add_argument(
            '--details',
            dest='details',
        )

    if cls.CAPS & usend.Capability.ATTACHMENTS:
        send_group.add_argument(
            '-a', '--attachment',
            dest='attachments',
            action='append'
        )


def main2():
    import sys

    # Minimal parser
    parser = get_basic_argument_parser()
    args, argv = parser.parse_known_args(sys.argv[1:])

    # Show help if not transport is specified
    if args.help and not args.transport:
        parser.print_help()
        return

    # Rebuild parser and reparse for transport
    if args.transport:
        parser = get_full_argument_parser(args.transport)
        args = parser.parse_args(sys.argv[1:])

    if args.help:
        parser.print_help()
        return

    # Load config if any
    config = load_config_files2(*args.config)

    print(repr(vars(args)))
    print(repr(config))

    if args.profile:
        params = config.get(args.profile)
    else:
        params = {}

    params.update({
        k: v
        for (k, v) in vars(args).items()
        if k not in ('help', 'config', 'profile')
    })

    transport = params.pop('transport')
    try:
        usend.send2(transport, **params)
    except usend.ParameterError as e:
        errmsg = (
            "Error: {e}\n" +
            "try using usend --transport {transport} --help"
        )
        errmsg = errmsg.format(e=e, transport=transport)
        print(errmsg, file=sys.stderr)


if __name__ == '__main__':
    main2()
