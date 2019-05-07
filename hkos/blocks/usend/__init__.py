class Transport(object):
    @classmethod
    def configure_argparser(cls, parser):
        """
        Support for command line application
        """
        if cls.CAPS & Capability.RECIEVER:
            parser.add_argument(
                '-t', '--to',
                dest='destination',
                required=True,
            )

        if cls.CAPS & Capability.ATTACHMENTS:
            parser.add_argument(
                '-a', '--attachment',
                dest='attachments',
                action='append'
            )

        if cls.CAPS & Capability.DETAILS:
            parser.add_argument(
                '--details',
                dest='details',
                nargs='?'
            )

        if cls.CAPS & Capability.MESSAGE:
            parser.add_argument(
                dest='message',
                nargs='?'
            )

    def send(self, to=None, message=None, details=None, attachments=None):
        """
        Send method
        """
        raise NotImplementedError()


class Capability(object):
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


class SendError(Exception):
    pass
