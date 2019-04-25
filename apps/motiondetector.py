#!/usr/bin/env python3

import hkos
import time
from datetime import datetime

try:
    import gi
except ImportError:
    import pgi as gi
    gi.install_as_gi()

gi.require_version('GLib', '2.0')
gi.require_version('Gst', '1.0')

from gi.repository import (  # noqa
    GLib,
    Gst
)


def parse_element_message(message):
    struct = message.get_structure()
    fields = [struct.nth_field_name(idx) for idx in range(struct.n_fields())]
    ret = {name: struct.get_value(name) for name in fields}
    return ret


class Motion(hkos.Beacon):
    EVENTS = ['ready', 'begin', 'finished', 'eos', 'error']

    MAIN = """
        v4l2src \
        ! image/jpeg,width=1280,height=720 \
        ! decodebin \
        ! videoconvert \
        ! tee name=output \
        ! videoscale \
        ! video/x-raw,width=160,height=120 \
        ! videoconvert \
        ! motioncells name=motion-detector gap=1 \
        ! queue \
        ! fakesink
    """

    SUB_PIPES = {
        'live': """
            queue name=live-input \
            ! xvimagesink async=true
        """,

        'snapshot': """
            queue name=capture-image-input \
            ! jpegenc snapshot=true \
            ! filesink location=a.jpg
        """,

        # ! encodebin profile=application/ogg:video/x-theora:audio/x-vorbis \
        'encode': """
            queue name=encode-input \
            ! theoraenc \
            ! oggmux \
            ! filesink location={output}.ogv
        """
    }

    def __init__(self):
        super().__init__()
        self.subpipelines = {}
        self._event_counter = 0

    def parse(self, desc, *args, **kwargs):
        try:
            return Gst.parse_launch(desc.strip(), *args, **kwargs)
        except GLib.Error as e:
            print(repr(e))
            raise

    def link(self, name, **params):
        description = self.SUB_PIPES[name].strip()
        description = description.format(**params)

        print("Connect", name, description)
        sub_pipe = self.parse(description)
        sub_pipe.name = name + '-pipeline'
        src = self.pipeline.get_by_name('output')
        sink = sub_pipe.get_by_name(name + '-input')
        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.add(sub_pipe)
        src.link(sink)
        self.pipeline.set_state(Gst.State.PLAYING)

        self.subpipelines[name] = sub_pipe
        return sub_pipe

    def unlink(self, name):
        if name not in self.subpipelines:
            return

        sink = self.pipeline.get_by_name(name + '-input')
        src = self.pipeline.get_by_name('output')

        self.pipeline.set_state(Gst.State.PAUSED)
        src.unlink(sink)
        self.pipeline.remove(self.subpipelines[name])
        self.subpipelines[name].set_state(Gst.State.NULL)
        del(self.subpipelines[name])
        self.pipeline.set_state(Gst.State.PLAYING)

    def snapshot(self):
        self.link('capture-image')

        # def on_msg(bus, msg):
        #     print("snapshot bus:", msg.type)
        #     return True

        # snapshot = self.link('capture-image', start=False)
        # snapshot.get_bus().add_watch(GLib.PRIORITY_DEFAULT, on_msg, None)
        # snapshot.set_state(Gst.State.PLAYING)

    def run(self):
        self.pipeline = self.parse(self.MAIN)
        self.pipeline.set_property("message-forward", True)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None

    def start_live(self):
        self.link('live')

    def stop_live(self):
        self.unlink('live')

    def start_capture(self, output):
        self.link('encode', output=output)

    def stop_capture(self):
        self.unlink('encode')

    def on_bus_message(self, bus, message):
        ignore_types = [
            Gst.MessageType.ASYNC_DONE,
            Gst.MessageType.NEW_CLOCK,
            Gst.MessageType.STREAM_START,
            Gst.MessageType.STREAM_STATUS,
        ]

        if message.type in ignore_types:
            return

        # msg = "[MSG] {name}\t{type}"
        # msg = msg.format(name=message.src.name,
        #                  type=str(message.type.first_value_name))
        # print(msg)

        # if message.type == Gst.MessageType.STATE_CHANGED:
        #     old, new, pending = message.parse_state_changed()
        #     print("({}) {} -> {}".format(pending, old, new))

        if message.type == Gst.MessageType.ELEMENT:
            msgparams = parse_element_message(message)
            # print("Message from", message.src.name)
            # print(repr(msgparams))

            if message.src is self.pipeline.get_by_name('motion-detector'):
                self.on_motion_detector_message(msgparams)

            else:
                # Handle messages from other elements
                pass

        elif message.type == Gst.MessageType.EOS:
            print("Got EOS from", message.src.name)
            self.emit('eos')

        elif message.type == Gst.MessageType.ERROR:
            gerror, strerror = message.parse_error()
            self.emit("error", gerror=gerror, strerror=strerror)

        else:
            pass

    def on_motion_detector_message(self, params):
        print(repr(params))
        if 'motion_begin' in params:
            ev = 'begin'
        elif 'motion_finished' in params:
            ev = 'finished'
        else:
            raise NotImplementedError()

        self._event_counter = self._event_counter + 1

        if self._event_counter == 2:
            self.emit('ready')

        if self._event_counter < 3:
            return

        self.emit(ev)


class App:
    def __init__(self):
        self.loop = GLib.MainLoop()
        self.motion = Motion()
        self.motion.watch('ready', lambda x: print("Ready"))
        self.motion.watch('begin', self.on_motion_begin)
        self.motion.watch('finished', self.on_motion_finished)
        self.motion.watch('eos', self.on_eos)
        self.motion.watch('error', self.on_error)

    def run(self):
        def _run():
            self.motion.run()
            return False

        GLib.idle_add(_run)
        self.loop.run()

    def quit(self):
        self.motion.stop()
        self.loop.quit()

    def on_motion_begin(self, _):
        print("Motion begin")
        self.motion.start_capture(datetime.now().strftime('%Y.%m.%d-%H.%M.%S'))
        self.motion.start_live()

    def on_motion_finished(self, _):
        print("Motion end")
        self.motion.stop_capture()
        self.motion.stop_live()

    def on_eos(self, _):
        self.quit()

    def on_error(self, _, gerror, strerror):
        print(gerror.message)


if __name__ == '__main__':
    Gst.init([])
    app = App()
    app.run()
