import usend


import email.mime.application
import email.mime.multipart
import email.mime.text
import email.utils
import os.path
import re
import smtplib


def check_is_email(s):
    return re.search(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', s)


class SMTP(usend.Transport):
    PARAMETERS = (
        usend.Parameter(
            'host',
            default='127.0.0.1'),
        usend.Parameter(
            'port',
            default=25,
            type=int),
        usend.Parameter(
            'sender',
            required=True),
    )
    CAPS = (usend.Capability.RECIEVER | usend.Capability.MESSAGE |
            usend.Capability.DETAILS | usend.Capability.ATTACHMENTS)

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
            raise ValueError(sender, 'not a valid email') from e
        if not check_is_email(self.sender):
            raise ValueError(self.sender, 'not a valid email')

        # Check port
        try:
            self.port = int(port)
        except ValueError as e:
            raise ValueError(port, 'invalid port') from e
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
        msg['Subject'] = message
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
