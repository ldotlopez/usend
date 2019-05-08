from hkos.blocks import classloader


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


def split_params(transport_cls, params):
    init_params = {}
    send_params = {}

    for (k, v) in params.items():
        if k.startswith(transport_cls.NAME + '_'):
            k = k[len(transport_cls.NAME) + 1:]
            init_params[k] = v
        else:
            send_params[k] = v

    transport = transport_cls(**init_params)

    return init_params, send_params


def build_transport(name, **params):
    loader = get_default_loader()
    cls = loader.get(name)
    init_params, send_params = split_params(cls, params)

    transport = cls(**init_params)
    return transport, send_params


class USendLoader(classloader.ClassLoader):
    PLUGINS = [
        ('null', 'hkos.blocks.usend.transports.Null'),
        ('mail', 'hkos.blocks.usend.transports.SMTP'),
        ('freedesktop', 'hkos.blocks.usend.transports.FreeDesktop'),
        ('macos', 'hkos.blocks.usend.transports.MacOSDesktop'),
        ('pushbullet', 'hkos.blocks.usend.transports.PushBullet'),
        ('telegram', 'hkos.blocks.usend.transports.Telegram'),
    ]

    def __init__(self):
        super().__init__(Transport)

    @classmethod
    def get_default(cls):
        self = cls()

        for (name, objpath) in self.PLUGINS:
            self.register(name, objpath)

        return self


def send(transport, transport_params, send_params):
    if isinstance(transport, str):
        loader = USendLoader.get_default()
        transport = loader.get(transport)

    if isinstance(transport, type) and issubclass(transport, Transport):
        if transport_params:
            transport = transport(**transport_params)
        else:
            transport = transport()

    if not isinstance(transport, Transport):
        raise TypeError(transport)

    return transport.send(**send_params)
