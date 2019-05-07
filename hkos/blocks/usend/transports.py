import sys
import subprocess


from hkos.blocks.usend import (Transport, Capability, SendError)


# 3rd parties
import requests


# SmtpTransport
import email.mime.application
import email.mime.multipart
import email.mime.text
import email.utils
import smtplib

# PushBullet
import pushbullet


# FreeDesktop
if sys.platform == 'linux':
    try:
        import gi
    except ImportError:
        import pgi as gi
        gi.install_as_gi()

    gi.require_version('Notify', '0.7')  # noqa
    from gi.repository import Notify


def check_is_email(s):
    return re.search(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', s)


class Null(Transport):
    NAME = 'null'
    CAPS = Capability.ALL

    def send(self, destination=None, message=None, details=None,
             attachments=None):
        pass


class SMTP(Transport):
    NAME = 'smtp'
    CAPS = (Capability.RECIEVER | Capability.MESSAGE | Capability.DETAILS |
            Capability.ATTACHMENTS)

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
        super().configure_argparser(parser)

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


class FreeDesktop(Transport):
    NAME = 'freedesktop'
    CAPS = Capability.MESSAGE | Capability.DETAILS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Notify.is_initted():
            Notify.init(sys.argv[0])

    def send(self, destination=None, message=None, details=None,
             attachments=None):
        ntfy = Notify.Notification(summary=message, body=details)
        ntfy.show()


class MacOSDesktop(Transport):
    NAME = 'macos'
    CAPS = Capability.MESSAGE | Capability.DETAILS

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
    CAPS = (Capability.RECIEVER | Capability.MESSAGE | Capability.DETAILS |
            Capability.ATTACHMENTS)

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


class PushBullet(Transport):
    """
    PushBullet transport
    """

    NAME = 'pushbullet'
    CAPS = (Capability.RECIEVER | Capability.MESSAGE | Capability.DETAILS |
            Capability.ATTACHMENTS)

    @classmethod
    def configure_argparser(self, parser):
        parser.add_argument(
            '--pushbullet-token',
            required=True
        )
        super(PushBullet, self).configure_argparser(parser)

    def __init__(self, token):
        token = str(token)
        if not token:
            msg = 'Missing pushbullet API token'
            raise ValueError(msg)

        self.pb = pushbullet.PushBullet(token)

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

    def send(self, destination, message, details='', attachments=None):
        try:
            device = self.pb.get_device(destination)
        except pushbullet.errors.PushbulletError as e:
            raise ValueError(destination) from e

        if not attachments:
            device.push_note(message, details)
            return

        composed = message
        if details:
            composed = "\n" + details

        for fp in attachments:
            with open(fp, 'rb') as fh:
                name = os.path.splitext(os.path.basename(fp))[0]
                uploaded = self.pb.upload_file(fh, name)
                self.pb.push_file(body=composed, **uploaded)
