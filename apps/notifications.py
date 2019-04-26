from hkos.blocks import (
    kvrouter,
    usend
)
from hkos.utils import (
    underscore_dict_keys,
    load_config_file
)
import functools
import sys


def send_wrapper(send_fn, **default_kwargs):
    @functools.wraps(send_fn)
    def _wrap(**kwargs):
        kw = {}
        kw.update(default_kwargs)
        kw.update(kwargs)
        return send_fn(**kw)

    return _wrap


class App:
    def __init__(self):
        config = self.get_config()

        self.router = kvrouter.Router()
        for (key, profile_name) in config['routes'].items():
            profile_params = config['profiles'][profile_name]
            profile_params = underscore_dict_keys(profile_params)
            transport, remaining = usend.build_transport(None, profile_params)
            self.router[key] = send_wrapper(transport.send, **remaining)

    @staticmethod
    def get_config():
        cp = load_config_file('notifications')

        # Load routes
        routes = {'*': 'null'}
        try:
            routes.update(cp['routes'].items())
        except KeyError:
            excmsg = "Missing routes from config"
            print(excmsg, file=sys.stderr)

        # Load (matching) profiles
        profiles = {}
        for (glob, profile_name) in routes.items():
            try:
                profiles[profile_name] = dict(cp[profile_name].items())
            except KeyError:
                excmsg = "Missing profile {profile} from config"
                excmsg = excmsg.format(profile=profile_name)
                print(excmsg, file=sys.stderr)

        ret = {
            'routes': routes,
            'profiles': profiles
        }

        return ret

    def notify(self, sender_id, message, details=None, attachments=None):
        fn = self.router.match(sender_id)
        fn(message=message, details=details, attachments=attachments)


def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--id',
        dest='sender_id',
        required=True,
    )
    parser.add_argument(
        '--details',
        dest='details'
    )
    parser.add_argument(
        '-a', '--attachment',
        dest='attachments',
        action='append'
    )
    parser.add_argument(
        dest='message',
    )
    args = parser.parse_args(sys.argv[1:])

    app = App()
    app.notify(args.sender_id, args.message,
               details=args.details,
               attachments=args.attachments)


if __name__ == '__main__':
    main()
