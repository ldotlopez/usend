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


def load_config_files(*config_filepaths):
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
        default=[],
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


def main():
    import sys

    # Minimal parser
    parser = get_basic_argument_parser()
    args, argv = parser.parse_known_args(sys.argv[1:])

    # Set some default config files if not provided from command line
    if not args.config:
        args.config = [
            os.path.expanduser('~/.config/usend.ini'),
            os.path.expanduser('~/.usend.ini')
        ]

    # Show help if not transport is specified
    if args.help and not args.transport:
        parser.print_help()
        return

    # Initialize params from config file (if any)
    params = {}
    if args.profile:
        config = load_config_files(*args.config)
        try:
            params.update(config[args.profile])
        except KeyError:
            errmsg = "Profile '{name}' not found"
            errmsg = errmsg.format(name=args.profile)
            print(errmsg, file=sys.stderr)
            return

    # Determine transport
    transport = params.pop('transport', None) or args.transport

    # Ful parse arguments
    parser = get_full_argument_parser(transport)
    args = parser.parse_args(sys.argv[1:])
    if args.help:
        parser.print_help()
        return

    # Merge params from command line
    params.update({
        k: v
        for (k, v) in vars(args).items()
        if k not in ('help', 'config', 'profile', 'transport') and v
    })

    # Send
    # transport = params.pop('transport')
    try:
        usend.send(transport, **params)
    except usend.ParameterError as e:
        errmsg = (
            "Error: {e}\n" +
            "try using usend --transport {transport} --help"
        )
        errmsg = errmsg.format(e=e, transport=transport)
        print(errmsg, file=sys.stderr)


if __name__ == '__main__':
    main()
