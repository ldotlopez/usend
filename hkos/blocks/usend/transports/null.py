import usend


class Transport(usend.Transport):
    CAPS = usend.Capability.ALL

    def send(self, destination=None, message=None, details=None,
             attachments=None):
        pass
