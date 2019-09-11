import usend
import sys


if sys.platform != 'linux':
    raise SystemError('FreeDesktop transport is only available on linux')


try:
    import gi
except ImportError:
    import pgi as gi
    gi.install_as_gi()

gi.require_version('Notify', '0.7')
from gi.repository import Notify  # noqa


class Transport(usend.Transport):
    PARAMETERS = ()
    CAPS = usend.Capability.MESSAGE | usend.Capability.DETAILS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not Notify.is_initted():
            Notify.init(sys.argv[0])

    def send(self, message=None, details=None):
        if not message:
            errmsg = "Message not provided"
            raise usend.ParameterError(errmsg)

        ntfy = Notify.Notification(summary=message, body=details)
        ntfy.show()
