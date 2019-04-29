import hkos
from hkos import utils
from hkos.blocks import kvrouter
from hkos.blocks import usend


import functools


def load_config():
    cp = utils.load_config_file('notifications')

    routes = {'*': 'null'}
    profiles = {'null': {'backend': 'null'}}

    try:
        routes.update(cp['routes'].items())
    except KeyError as e:
        excmsg = "Missing section 'routes'"
        raise hkos.ConfigurationError(excmsg) from e

    for (route_name, profile_name) in routes.items():
        try:
            profile_params = dict(cp[profile_name].items())

        except KeyError as e:
            excmsg = ("Missing profile '{profile}' referenced "
                      "from route '{route}'")
            excmsg = excmsg.format(profile=profile_name, route=route_name)
            raise hkos.ConfigurationError(excmsg) from e

        profiles[profile_name] = profile_params

    ret = {
        'routes': routes,
        'profiles': profiles
    }
    return ret


def build_send_wrapper(send_fn, **default_kwargs):
    @functools.wraps(send_fn)
    def _wrap(**kwargs):
        kw = {}
        kw.update(default_kwargs)
        kw.update(kwargs)
        return send_fn(**kw)

    return _wrap


class Notifications:
    def __init__(self):
        config = load_config()
        self.router = kvrouter.Router()
        for (key, profile_name) in config['routes'].items():
            profile_params = config['profiles'][profile_name]
            profile_params = utils.underscore_dict_keys(profile_params)
            transport, remaining = usend.build_transport(None, profile_params)
            self.router[key] = build_send_wrapper(transport.send, **remaining)

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

    ntfy = Notifications()
    ntfy.notify(args.sender_id, args.message,
                details=args.details,
                attachments=args.attachments)


if __name__ == '__main__':
    main()
