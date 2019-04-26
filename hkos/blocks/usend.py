#!/usr/bin/env python3

# py2/py3 compat
from __future__ import print_function
from six import raise_from
from six.moves import configparser


# stdlib
import argparse
import os.path
import re
import subprocess
import sys
from io import open


# 3rd parties
import requests


# SmtpTransport
import email.mime.application
import email.mime.multipart
import email.mime.text
import email.utils
import smtplib


def check_is_email(s):
    return re.search(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', s)


class TransportNotFound(Exception):
    pass


class SendError(Exception):
    pass


class Transport(object):
    @classmethod
    def configure_argparser(cls, parser):
        """
        Support for command line application
        """
        if cls.CAPS & Cap.RECIEVER:
            parser.add_argument(
                '-t', '--to',
                dest='destination',
                required=True,
            )

        if cls.CAPS & Cap.ATTACHMENTS:
            parser.add_argument(
                '-a', '--attachment',
                dest='attachments',
                action='append'
            )

        if cls.CAPS & Cap.DETAILS:
            parser.add_argument(
                '--details',
                dest='details',
                nargs='?'
            )

        if cls.CAPS & Cap.MESSAGE:
            parser.add_argument(
                dest='message',
                nargs='?'
            )

    def send(self, to=None, message=None, details=None, attachments=None):
        raise NotImplementedError()


class Cap(object):
    NONE = 0
    RECIEVER = 1 << 1
    MESSAGE = 1 << 2
    DETAILS = 1 << 3
    ATTACHMENTS = 1 << 4
    ALL = (
        RECIEVER |
        MESSAGE |
        DETAILS |
        ATTACHMENTS
    )


class Null(Transport):
    NAME = 'null'
    CAPS = Cap.ALL

    def send(self, destination, message, details='', attachments=None):
        pass


class SMTP(Transport):
    NAME = 'smtp'
    CAPS = (Cap.RECIEVER | Cap.MESSAGE | Cap.DETAILS | Cap.ATTACHMENTS)

    @classmethod
    def configure_argparser(cls, parser):
        parser.add_argument(
            '--smtp-host',
            default='127.0.0.1'
        )
        parser.add_argument(
            '--smtp-port',
            default=25,
            type=int
        )
        parser.add_argument(
            '--smtp-sender',
            type=str,
            required=True
        )
        super(SMTP, cls).configure_argparser(parser)

    def __init__(self, sender, host='127.0.0.1', port=25):
        self.host = str(host)
        self.port = int(port)

        # check sender
        try:
            self.sender = str(sender)
        except ValueError as e:
            raise_from(ValueError(sender, 'not a valid email'), e)
        if not check_is_email(self.sender):
            raise ValueError(self.sender, 'not a valid email')

        # Check port
        try:
            self.port = int(port)
        except ValueError as e:
            raise_from(ValueError(port, 'invalid port'), e)
        if self.port < 1:
            raise ValueError(port, 'invalid port')

    def send(self, destination, message=None, details=None, attachments=None):
        # check destination
        if not check_is_email(destination):
            raise ValueError(destination, 'not a valid email')

        # Check message
        message = str(message)
        if not message:
            raise ValueError(message, 'empty message')

        if not message and not details:
            raise ValueError((message, details), 'message or details required')

        if not details:
            message, details = ("Notification from HkOS", message)

        msg = email.mime.multipart.MIMEMultipart()
        msg['From'] = self.sender
        # msg['To'] = email.utils.COMMASPACE.join(send_to)
        msg['To'] = destination
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Subject'] = subject
        msg.attach(email.mime.text.MIMEText(message))

        for f in attachments or []:
            with open(f, "rb") as fh:
                part = email.mime.application.MIMEApplication(
                    fh.read(),
                    Name=os.path.basename(f))

            part['Content-Disposition'] = ('attachment; filename="%s"' %
                                           os.path.basename(f))
            msg.attach(part)

        smtp = smtplib.SMTP(self.host, port=self.port)
        smtp.sendmail(self.sender, destination, msg.as_string())
        smtp.close()


class MacOSDesktop(Transport):
    NAME = 'macos-desktop'
    CAPS = Cap.MESSAGE | Cap.DETAILS

    SCRIPT = 'display notification "{body}" with title "{message}"'

    def send(self, destination=None, message=None, details=None,
             attachments=None):
        if not message and not details:
            raise ValueError((message, details), 'message or details required')

        script = self.SCRIPT
        script = script.format(message=message, body=details or '')
        cmdl = ['/usr/bin/osascript', '-e', script]

        try:
            subprocess.check_output(cmdl)

        except FileNotFoundError:
            msg = "osascript not found"
            raise SendError(msg)

        except subprocess.CalledProcessError as e:
            msg = "subprocess failed: {cmdl}, code={code}"
            msg = msg.format(cmdl=repr(cmdl), code=e.returncode)
            raise SendError(msg)


class Telegram(Transport):
    """
    Telegram backend.
    Docs: https://core.telegram.org/bots/api
    """

    NAME = 'telegram'
    CAPS = Cap.RECIEVER | Cap.MESSAGE | Cap.DETAILS | Cap.ATTACHMENTS

    BASE_API_URL = 'https://api.telegram.org/bot{token}'

    @classmethod
    def configure_argparser(self, parser):
        parser.add_argument(
            '--telegram-token',
            required=True
        )
        super(Telegram, self).configure_argparser(parser)

    def __init__(self, token):
        token = str(token)
        if not token:
            msg = 'Missing telegram token'
            raise ValueError(msg)

        self.BASE_API_URL = self.BASE_API_URL.format(token=token)

    def check_response(self, resp):
        if resp.status_code != 200:
            errmsg = 'code={code}, description={description}'
            errmsg = errmsg.format(code=resp.status_code,
                                   description=resp.json()['description'])
            raise SendError(errmsg)

        resp = resp.json()
        if not resp.get('ok'):
            raise SendError(repr(resp))

        return resp['result']

    def send(self, destination, message, details=None, attachments=None):
        try:
            destination = int(destination)
        except ValueError:
            url = self.BASE_API_URL + '/getUpdates'
            resp = requests.get(url)
            resp = self.check_response(resp)
            tbl = {
                x['message']['chat']['username']: x['message']['chat']['id']
                for x in resp if 'message' in x and 'chat' in x['message']
            }
            try:
                destination = tbl[destination]
            except KeyError as e:
                errmsg = ("user {username} not found. "
                          "(try sending /start to the bot)")
                errmsg = errmsg.format(username=destination)
                raise raise_from(SendError(errmsg), e)

        if not attachments:
            attachments = []

        tg_data = {
            'chat_id': destination,
            'text': message,
            'parse_mode': None,
            'caption': None
        }

        # Merge message and details
        if details:
            message = "*{message}*\n{details}".format(
                message=message,
                details=details)
            parse_mode = 'markdown'
        else:
            parse_mode = None

        if (not attachments or
                (len(attachments) == 1 and len(message) > 1024) or
                len(attachments) > 1):
            tg_data = {
                'chat_id': destination,
                'text': message,
                'parse_mode': parse_mode
            }
            url = self.BASE_API_URL + '/sendMessage'
            resp = requests.get(url, data=tg_data)
            self.check_response(resp)
            message = None

        tg_data = {
            'chat_id': destination,
            'caption': message,
            'parse_mode': parse_mode
        }
        for filepath in attachments:
            files = {'document': open(filepath, 'rb')}
            url = self.BASE_API_URL + '/sendDocument'
            resp = requests.post(url, data=tg_data, files=files)
            self.check_response(resp)


def build_transport(cls_or_name, params):
    if isinstance(cls_or_name, str):
        cls = transport_for_name(cls_or_name)
    elif isinstance(cls_or_name, Transport):
        cls = cls_or_name
    elif cls_or_name is None:
        cls = transport_for_name(params.pop('backend'))
    else:
        raise TypeError(cls_or_name,
                        'Transport class, string or None required')

    if not isinstance(params, dict):
        raise TypeError(params, 'dict required')

    # Extract Transport.__init__ params
    init_params = {}
    remaining = {}

    for (k, v) in params.items():
        if k.startswith(cls.NAME + '_'):
            k = k[len(cls.NAME) + 1:]
            init_params[k] = v
        else:
            remaining[k] = v

    transport = cls(**init_params)

    return transport, remaining


def transport_for_name(name, cls=Transport):
    if getattr(cls, 'NAME', '') == name:
        return cls

    for subcls in cls.__subclasses__():
        try:
            return transport_for_name(name, cls=subcls)
        except TransportNotFound:
            pass

    raise TransportNotFound()


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


def configure_argparser_for_transport(parser, cls):
    # if cls.CAPS & Cap.SENDER:
    #     parser.add_argument(
    #         '-f', '--from',
    #         dest='send_from',
    #         required=True,
    #     )
    if cls.CAPS & Cap.RECIEVER:
        parser.add_argument(
            '-t', '--to',
            dest='send_to',
            required=True,
        )

    if cls.CAPS & Cap.MESSAGE:
        parser.add_argument(
            dest='message',
            nargs='?'
        )

    if cls.CAPS & Cap.DETAILS:
        parser.add_argument(
            dest='details',
            nargs='?'
        )

    if cls.CAPS & Cap.ATTACHMENTS:
        parser.add_argument(
            '-a', '--attachment',
            dest='attachments',
            action='append'
        )


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
    transport_cls = transport_for_name(transport_name)
    transport_cls.configure_argparser(parser)

    # Cleanup params
    args = parser.parse_args(sys.argv[1:])
    if args.help:
        parser.print_help()
        sys.exit(1)

    params = vars(args)
    for k in ['config_file', 'profile_name', 'transport_name']:
        params.pop(k, None)

    transport, send_params = build_transport(transport_name, params)
    try:
        transport.send(**send_params)
    except SendError as e:
        msg = "Send failed: {err}"
        msg = msg.format(err=str(e))
        print(msg, file=sys.stderr)


if __name__ == '__main__':
    main()
