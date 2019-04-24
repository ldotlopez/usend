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
    PIPELINE = """
    v4l2src ! decodebin ! videoconvert ! motioncells name=motion ! videoconvert ! autovideosink
    """

    def __init__(self):
        pass

    def run(self):
        def _run():
            self.pipeline = Gst.parse_launch(self.PIPELINE.strip())
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
            import ipdb; ipdb.set_trace(); pass

        elif message.type == Gst.MessageType.ELEMENT:
            print("Message from", message.src.name)
            print(repr(parse_element_message(message)))

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
