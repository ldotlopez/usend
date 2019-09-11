import usend


import requests


class Transport(usend.Transport):
    """
    Telegram backend.
    Docs: https://core.telegram.org/bots/api
    """

    PARAMETERS = (
        usend.Parameter(
            'token',
            required=True),
    )
    CAPS = (usend.Capability.RECIEVER | usend.Capability.MESSAGE |
            usend.Capability.DETAILS | usend.Capability.ATTACHMENTS)

    BASE_API_URL = 'https://api.telegram.org/bot{token}'

    @classmethod
    def configure_argparser(self, parser):
        parser.add_argument(
            '--telegram-token',
            required=True
        )
        super(Transport, self).configure_argparser(parser)

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
            raise usend.SendError(errmsg)

        resp = resp.json()
        if not resp.get('ok'):
            raise usend.SendError(repr(resp))

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
                raise usend.SendError(errmsg) from e

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
