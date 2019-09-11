import importlib
import re


class Parameter:
    def __init__(self, name, required=False, type=str, default=None):
        self.name = name
        self.required = required
        self.type = type
        self.default = default


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


class Transport(object):
    PARAMETERS = ()
    CAPS = Capability.NONE

    @classmethod
    def name(cls):
        bname = cls.__module__.split('.')[-1]
        simplified = re.sub(r'[^a-zA-Z]+', '-', bname, flags=re.IGNORECASE).lower().strip('-')
        return simplified

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


class ParameterError(Exception):
    pass


class SendError(Exception):
    pass


def split_params(transport_cls, **params):
    init_params = {}
    send_params = {}

    transport_name = transport_cls.__module__.split('.')[-1]

    for (k, v) in params.items():
        if k.startswith(transport_name + '_'):
            k = k[len(transport_name) + 1:]
            init_params[k] = v
        else:
            send_params[k] = v

    return init_params, send_params


def get_transport(name):
    try:
        m = importlib.import_module('usend.transports.' + name)
    except ImportError as e:
        print("Can't load transport: {}".format(e))
        raise

    try:
        cls = getattr(m, 'Transport')
    except AttributeError:
        print("Invalid plugin")
        raise

    return cls


def send(transport, transport_params, send_params):
    if isinstance(transport, str):
        transport = get_transport(transport)

    if isinstance(transport, type) and issubclass(transport, Transport):
        if transport_params:
            transport = transport(**transport_params)
        else:
            transport = transport()

    if not isinstance(transport, Transport):
        raise TypeError(transport)

    return transport.send(**send_params)


def send2(transport, **params):
    if isinstance(transport, type) and \
            issubclass(transport, Transport) and \
            type(transport) != Transport:
        transport_cls = transport
    elif isinstance(transport, str):
        transport_cls = get_transport(transport)
    else:
        err = "transport must be a str or a Trasport subclass"
        raise TypeError(err)

    transport_params, send_params = split_params(transport_cls, **params)
    transport = transport_cls(**transport_params)
    return transport.send(**send_params)
