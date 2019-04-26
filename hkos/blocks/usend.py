#!/usr/bin/env python3

# py2/py3 compat
from __future__ import print_function
from six import raise_from
from six.moves import configparser


# stdlib
import argparse
import json
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
    # @classmethod
    # def get(cls, name):
    #     for subcls in cls.__subclasses__():
    #         try:
    #             return subcls.get(name)
    #         except TransportNotFound:
    #             pass

    #     if getattr(cls, 'NAME', '') == name:
    #         return cls

    #     raise TransportNotFound()

    @classmethod
    def configure_argparser(cls, parser):
        pass

    def send(self, send_to, message, body=None, attachments=None):
        raise NotImplementedError()


class Cap(object):
    NONE = 0
    SENDER = 1
    RECIEVER = 1 << 1
    MESSAGE = 1 << 2
    DETAILS = 1 << 3
    ATTACHMENTS = 1 << 4
    ALL = (
        SENDER |
        RECIEVER |
        MESSAGE |
        DETAILS |
        ATTACHMENTS
    )

# class SenderMixin(object):
#     @classmethod
#     def configure_argparser(cls, parser):
#         super(SenderMixin, cls).configure_argparser(parser)
#         parser.add_argument(
#             '-f', '--from',
#             dest='send_from',
#             required=True,
#         )


# class RecieverMixin(object):
#     @classmethod
#     def configure_argparser(cls, parser):
#         super(RecieverMixin, cls).configure_argparser(parser)
#         parser.add_argument(
#             '-t', '--to',
#             dest='send_to',
#             required=True,
#         )


# class MessageMixin(object):
#     @classmethod
#     def configure_argparser(cls, parser):
#         super(MessageMixin, cls).configure_argparser(parser)
#         parser.add_argument(
#             dest='message',
#             nargs='?'
#         )


# class AttachmentMixin(object):
#     @classmethod
#     def configure_argparser(cls, parser):
#         super(AttachmentMixin, cls).configure_argparser(parser)
#         parser.add_argument(
#             '-a', '--attachment',
#             dest='attachments',
#             action='append'
#         )


class Null(Transport):
    NAME = 'null'
    CAPS = Cap.ALL

    def send(self, destination, message, details='', attachments=None):
        pass


class SMTP(Transport):
    NAME = 'smtp'
    CAPS = (Cap.SENDER | Cap.RECIEVER | Cap.MESSAGE | Cap.DETAILS |
            Cap.ATTACHMENTS)

    @classmethod
    def configure_argparser(cls, parser):
        super(SMTP, cls).configure_argparser(parser)
        parser.add_argument(
            '--smtp-host',
            default='127.0.0.1'
        )
        parser.add_argument(
            '--smtp-port',
            default=25,
            type=int)

    def __init__(self, host='127.0.0.1', port=25):
        self.host = str(host)
        self.port = int(port)

        # Check port
        try:
            self.port = int(port)
        except ValueError as e:
            raise_from(ValueError(port, 'invalid port'), e)
        if self.port < 1:
            raise ValueError(port, 'invalid port')

    def send(self, send_from, send_to, message, subject='', attachments=None):
        # check send_from
        if not check_is_email(send_from):
            raise ValueError(send_from, 'not a valid email')

        # check send_to
        if not isinstance(send_to, list):
            send_to = [send_to]
        if not all([check_is_email(x) for x in send_to]):
            raise ValueError(send_to, 'not a list of valid emails')

        # Check message
        message = str(message)
        if not message:
            raise ValueError(message, 'empty message')

        msg = email.mime.multipart.MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = email.utils.COMMASPACE.join(send_to)
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
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.close()


class MacOSDesktop(Transport):
    NAME = 'macos-desktop'
    CAPS = Cap.MESSAGE | Cap.DETAILS

    SCRIPT = 'display notification "{body}" with title "{message}"'

    def send(self, message, body=None, attachments=None):
        script = self.SCRIPT
        script = script.format(message=message, body=body or '')
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
    NAME = 'telegram'
    CAPS = Cap.RECIEVER | Cap.MESSAGE | Cap.ATTACHMENTS

    API = 'https://api.telegram.org/bot{token}'

    @classmethod
    def configure_argparser(self, parser):
        super(Telegram, self).configure_argparser(parser)
        parser.add_argument(
            '--telegram-token',
            required=True
        )

    def __init__(self, token):
        token = str(token)
        if not token:
            msg = 'Missing telegram token'
            raise ValueError(msg)

        self.API = self.API.format(token=token)

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

    def send(self, send_to, message, attachments=None):
        try:
            send_to = int(send_to)
        except ValueError:
            url = self.API + '/getUpdates'
            resp = requests.get(url)
            resp = self.check_response(resp)
            tbl = {
                x['message']['chat']['username']: x['message']['chat']['id']
                for x in resp if 'message' in x and 'chat' in x['message']
            }
            try:
                send_to = tbl[send_to]
            except KeyError as e:
                errmsg = ("user {username} not found. "
                          "(try sending /start to the bot)")
                errmsg = errmsg.format(username=send_to)
                raise raise_from(SendError(errmsg), e)

        caption = None
        if attachments and message and len(message) <= 1024:
            message, caption = None, message

        if message:
            url = self.API + '/sendMessage'
            data = {'chat_id': send_to, 'text': message}
            resp = requests.get(url, data=data)
            self.check_response(resp)

        if attachments:
            url = self.API + '/sendDocument'
            data = {'chat_id': send_to, 'caption': caption}

            for filepath in attachments:
                files = {'document': open(filepath, 'rb')}
                resp = requests.post(url, data=data, files=files)
                self.check_response(resp)


def get(name, cls=Transport):
    if getattr(cls, 'NAME', '') == name:
        return cls

    for subcls in cls.__subclasses__():
        try:
            return get(name, cls=subcls)
        except TransportNotFound:
            pass

    raise TransportNotFound()


def load_profile(config, profile):
    ret = {}
    if not config.has_section(profile):
        raise KeyError(profile)

    for (name, value) in config.items(profile):
        ret[name] = value

    try:
        includes = re.split(r"[\s,]+", ret.pop('include'))
    except KeyError:
        return ret

    for x in includes:
        ret.update(load_profile(config, x))

    return ret


def configure_argparser_for(parser, cls):
    if cls.CAPS & Cap.SENDER:
        parser.add_argument(
            '-f', '--from',
            dest='send_from',
            required=True,
        )

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

    if cls.CAPS & Cap.ATTACHMENTS:
        parser.add_argument(
            '-a', '--attachment',
            dest='attachments',
            action='append'
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--transport',
        default='',
        help='Transport to use.'
    )
    parser.add_argument(
        '--profile',
        default='',
    )

    # TODO: Parse config file from command line
    config = configparser.ConfigParser()
    configfiles = [
        os.path.expanduser('~/.config/usend.ini'),
        os.path.expanduser('~/.usend.ini')
    ]
    for configfile in configfiles:
        try:
            with open(configfile, 'r', encoding='utf-8') as fh:
                config.read_file(fh)
            break

        except OSError as e:
            errmsg = "Can't read configfile '{filepath}': {msg}"
            errmsg = errmsg.format(filepath=configfile, msg=str(e))
            print(errmsg, file=sys.stderr)

    # Initial argument parsing
    args, remaining = parser.parse_known_args(sys.argv[1:])

    # If profile it's specified we load it and integrate its values as
    # arguments
    if args.profile:
        profile_items = load_profile(config, args.profile)
    else:
        profile_items = {}

    # Check which transport to use (pop from profile_items)
    transport_name = (
        args.transport or
        profile_items.get('transport', None)
        or ''
    )
    if not transport_name:
        print("Transport param is required", file=sys.stderr)
        sys.exit(1)

    try:
        transport_cls = get(transport_name)
    except TransportNotFound:
        msg = "Transport '{transport}' not found"
        print(msg.format(transport=transport_name))
        sys.exit(1)

    # Integrate profile items into remaining args
    profile_argv = []
    profile_items.pop('transport', None)
    for (name, value) in profile_items.items():
        profile_argv.extend(['--' + name.replace('_', '-'), value])
    remaining = profile_argv + remaining

    # Parse remaining command line with transport parser
    # transport_cls.configure_argparser(parser)
    configure_argparser_for(parser, transport_cls)
    transport_cls.configure_argparser(parser)
    args = parser.parse_args(remaining)

    # Split into init and send params
    init_params = {}
    send_params = {}
    for (name, value) in vars(args).items():
        if name in ('transport', 'profile'):
            pass
        elif name.startswith(transport_name + '_'):
            real_name = name[len(transport_name) + 1:]
            init_params[real_name] = value
        else:
            send_params[name] = value

    transport = transport_cls(**init_params)

    try:
        transport.send(**send_params)
    except SendError as e:
        msg = "Send failed: {err}"
        msg = msg.format(err=str(e))
        print(msg, file=sys.stderr)


if __name__ == '__main__':
    main()
