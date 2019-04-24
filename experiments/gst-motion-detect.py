#!/usr/bin/env python3

import gi
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


class App():
    """
    gst-launch-1.0 -m v4l2src ! 'image/jpeg,width=1280,height=720' ! decodebin ! tee name=t \
        t. ! queue ! xvimagesink async=true \
        t. ! queue ! videoconvert ! motioncells ! fakesink
    """
    PIPELINE = """
    v4l2src ! 'image/jpeg,width=1280,height=720' ! decodebin ! tee name=t \
        t. ! queue ! xvimagesink async=true \
        t. ! queue ! videoscale ! 'video/x-raw,width=160,height=120' ! videoconvert ! motioncells gap=1 ! fakesink
    """

    # VIDEOSRC = "v4l2src ! 'image/jpeg,width=1280,height=720' ! decodebin ! tee name=output ! autovideosink"
    MAIN = """
        v4l2src ! image/jpeg,width=1280,height=720 ! decodebin ! videoconvert ! tee name=output \
        ! videoscale ! video/x-raw,width=160,height=120 ! videoconvert ! motioncells gap=1 ! fakesink
    """
    LIVE = "queue name=live-input ! xvimagesink async=true"

    def __init__(self):
        self.subpipelines = {}
        self.motion_ready = False

    def parse(self, desc, *args, **kwargs):
        try:
            return Gst.parse_launch(desc.strip(), *args, **kwargs)
        except GLib.Error as e:
            print(repr(e))
            raise

    def link(self, name, description):
        print("Connect", name, description.strip())
        subpipeline = self.parse(description.strip())
        src = self.pipeline.get_by_name('output')
        sink = subpipeline.get_by_name(name + '-input')
        self.pipeline.add(subpipeline)
        src.link(sink)
        subpipeline.set_state(Gst.State.PLAYING)
        self.subpipelines[name] = subpipeline

    def unlink(self, name):
        if name not in self.subpipelines:
            return

        sink = self.pipeline.get_by_name(name + '-input')
        src = self.pipeline.get_by_name('output')
        src.unlink(sink)

        self.pipeline.remove(self.subpipelines[name])
        self.subpipelines[name].set_state(Gst.State.NULL)
        del(self.subpipelines[name])

    def capture(self):
        self.link('live', self.LIVE)

    def uncapture(self):
        self.unlink('live')

    def run(self):
        def _run():
            self.pipeline = self.parse(self.MAIN)
            bus = self.pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self.on_bus_message)
            self.pipeline.set_state(Gst.State.PLAYING)
            return False

        GLib.idle_add(_run)

    def on_bus_message(self, bus, message):
        ignore_types = [
            Gst.MessageType.ASYNC_DONE,
            # Gst.MessageType.ELEMENT,
            Gst.MessageType.NEW_CLOCK,
            Gst.MessageType.STATE_CHANGED,
            Gst.MessageType.STREAM_START,
            Gst.MessageType.STREAM_STATUS,
        ]

        if message.type in ignore_types:
            return

        if message.type == Gst.MessageType.ERROR:
            errglib, errstr = message.parse_error()
            print(errglib.message)

        elif message.type == Gst.MessageType.ELEMENT:
            print("Message from", message.src.name)
            msgparams = parse_element_message(message)
            print(repr(msgparams))

            if 'motion_begin' in msgparams:
                if self.motion_ready:
                    self.capture()
                else:
                    self.motion_ready = True

            if 'motion_finished' in msgparams and self.motion_ready:
                self.uncapture()

        elif message.type == Gst.MessageType.EOS:
            print("Got EOS")

        else:
            print(message.type)


if __name__ == '__main__':
    Gst.init([])
    loop = GLib.MainLoop()
    app = App()
    app.run()
    loop.run()
