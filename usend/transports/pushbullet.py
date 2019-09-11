import usend


import os.path


import pushbullet


class Transport(usend.Transport):
    """
    PushBullet transport
    """
    PARAMETERS = (
        usend.Parameter('token', required=True, type=str),
    )

    CAPS = (usend.Capability.RECIEVER | usend.Capability.MESSAGE |
            usend.Capability.DETAILS | usend.Capability.ATTACHMENTS)

    @classmethod
    def configure_argparser(self, parser):
        parser.add_argument(
            '--pushbullet-token',
            required=True
        )
        super(Transport, self).configure_argparser(parser)

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
            raise usend.SendError(errmsg)

        resp = resp.json()
        if not resp.get('ok'):
            raise usend.SendError(repr(resp))

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
