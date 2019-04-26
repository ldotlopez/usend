import hkos
from hkos.blocks import (
    kvrouter,
    usend
)

import collections
import functools
import sys


def underscore_dict_keys(d, recurse=True):
    ret = {}
    for (k, v) in d.items():
        k = k.replace('-', '_')
        if isinstance(v, dict) and recurse:
            v = underscore_dict_keys(v, recurse=True)
        ret[k] = v

    return ret


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
        cp = hkos.load_config_file('notifications')

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
    app = App()
    app.notify('motiondetector.cam0.motion', 'hola')


if __name__ == '__main__':
    main()
