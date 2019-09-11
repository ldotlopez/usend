import usend


import sys
import subprocess


if sys.platform != 'darwin':
    raise SystemError('MacOS transport is only available on MacOS')


class Transport(usend.Transport):
    CAPS = usend.Capability.MESSAGE | usend.Capability.DETAILS

    SCRIPT = 'display notification "{body}" with title "{message}"'

    def send(self, message=None, details=None):
        if not message and not details:
            raise ValueError((message, details), 'message or details required')

        script = self.SCRIPT
        script = script.format(message=message, body=details or '')
        cmdl = ['/usr/bin/osascript', '-e', script]

        try:
            subprocess.check_output(cmdl)

        except FileNotFoundError:
            msg = "osascript not found"
            raise usend.SendError(msg)

        except subprocess.CalledProcessError as e:
            msg = "subprocess failed: {cmdl}, code={code}"
            msg = msg.format(cmdl=repr(cmdl), code=e.returncode)
            raise usend.SendError(msg)
