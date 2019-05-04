#!/usr/bin/env python3


from hkos.blocks.beacon import Beacon


import contextlib
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
    try:
        ret = {name: struct.get_value(name) for name in fields}
    except TypeError:
        return {}

    return ret


class Motion(Beacon):
    EVENTS = ['ready', 'begin', 'finished', 'eos', 'error']

    MAIN = """
        {src} \
        ! decodebin \
        ! video/x-raw ! videoconvert \
        ! tee name=output \
        output. \
            ! queue \
            ! videoconvert \
            ! videoscale ! video/x-raw,width=160,height=120 \
            ! videoconvert \
            ! motioncells name=motion-detector gap={motion_gap} \
            ! videoconvert \
            ! queue \
            ! fakesink
    """

    BRANCHES = {
        'live': """
            queue name=live-input \
            ! videoconvert \
            ! queue \
            ! xvimagesink
        """,

        'snapshot': """
            queue name=snapshot-input \
            ! jpegenc \
            ! filesink name=snapshot-filesink location={snapshot_output}.jpg
        """,

        'encode': """
            queue name=encode-input \
            ! videoconvert \
            ! x264enc \
            ! mp4mux fragment-duration=200 \
            ! queue \
            ! filesink async=false location={encode_output}.mp4
        """
    }

    def __init__(self, src='v4l2src device=/dev/video0', gap=3):
        super().__init__()
        self.MAIN = self.MAIN.format(
            src=src.strip().strip('!'),
            motion_gap=gap)

        self.subpipelines = {}

    def parse(self, desc, *args, **kwargs):
        try:
            return Gst.parse_launch(desc.strip(), *args, **kwargs)
        except GLib.Error as e:
            print(repr(e))
            raise

    @contextlib.contextmanager
    def pause(self):
        def check_state(e, state):
            ret_type, state, pending = e.get_state(Gst.CLOCK_TIME_NONE)
            if pending != Gst.State.VOID_PENDING:
                raise SystemError()
            if state != state:
                raise SystemError()

        e = self.pipeline

        e.set_state(Gst.State.PAUSED)
        check_state(e, Gst.State.PAUSED)

        yield self.pipeline

        e.set_state(Gst.State.PLAYING)
        check_state(e, Gst.State.PLAYING)

    def link(self, name, play=True, pipeline_params=None):
        if pipeline_params is None:
            pipeline_params = {}

        desc = self.BRANCHES[name].strip()
        desc = desc.format(**pipeline_params)

        print("Connect", name, desc)
        branch = self.parse(desc)
        branch.name = name + '-pipeline'
        src = self.pipeline.get_by_name('output')
        sink = branch.get_by_name(name + '-input')

        self.pipeline.set_state(Gst.State.PAUSED)

        self.pipeline.add(branch)
        src.link(sink)

        if play:
            self.pipeline.set_state(Gst.State.PLAYING)

        self.subpipelines[name] = branch
        return branch

    def unlink(self, name):
        if name not in self.subpipelines:
            return

        src = self.pipeline.get_by_name('output')
        sink = self.pipeline.get_by_name(name + '-input')

        with self.pause():
            src.unlink(sink)
            self.pipeline.remove(self.subpipelines[name])

        self.subpipelines[name].set_state(Gst.State.NULL)
        del(self.subpipelines[name])

    def run(self):
        self.pipeline = self.parse(self.MAIN)
        self.pipeline.set_property("message-forward", True)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        self._start_time = time.monotonic()
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None

    def start_live(self):
        self.link('live')

    def stop_live(self):
        self.unlink('live')

    def start_capture(self, output):
        self.link('encode', pipeline_params={'encode_output': output})

    def stop_capture(self):
        self.unlink('encode')

    def snapshot(self, output):
        done = False
        finalize_sched = False

        def pad_probe(pad, info):
            nonlocal done, finalize_sched

            if not done:
                return Gst.PadProbeReturn.PASS

            if not finalize_sched:
                finalize_sched = True
                GLib.idle_add(_finalize_snapshot)

            return Gst.PadProbeReturn.DROP

        def _finalize_snapshot():
            self.unlink('snapshot')
            return False

        branch = self.link(
            'snapshot',
            play=False,
            pipeline_params={'snapshot_output': output})

        filesink = branch.get_by_name('snapshot-filesink')
        assert(len(filesink.sinkpads) == 1)

        pad = filesink.sinkpads[0]
        pad.add_probe(Gst.PadProbeType.BUFFER, pad_probe)

        self.pipeline.set_state(Gst.State.PLAYING)

    def debug_message(self, message):
        return
        ignore_types = [
            Gst.MessageType.ASYNC_DONE,
            Gst.MessageType.NEW_CLOCK,
            Gst.MessageType.STREAM_START,
            Gst.MessageType.STREAM_STATUS,
        ]

        if message.type in ignore_types:
            return

        msg = "[MSG] {name}\t{type}"
        msg = msg.format(name=message.src.name,
                         type=str(message.type.first_value_name))
        print(msg)

        if message.type == Gst.MessageType.STATE_CHANGED:
            old, new, pending = message.parse_state_changed()
            print("({}) {} -> {}".format(pending, old, new))

    def on_bus_message(self, bus, message):
        self.debug_message(message)
        if message.src.name == 'snapshot-encoder' or message.src == self.subpipelines.get('snapshot'):
            self.debug_message(message)

        if message.type == Gst.MessageType.ELEMENT:
            msgparams = parse_element_message(message)
            # print("Message from", message.src.name)
            # print(repr(msgparams))

            if message.src is self.pipeline.get_by_name('motion-detector'):
                self.on_motion_detector_message(msgparams)

            else:
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
        if 'motion_begin' in params:
            ev = 'begin'
        elif 'motion_finished' in params:
            ev = 'finished'
        else:
            raise NotImplementedError()

        self.emit(ev)


class App:
    def __init__(self):
        self.loop = GLib.MainLoop()
        self.motion = Motion(
            # src=("v4l2src device=/dev/video2 "
            #      "! image/jpeg,width=1280,height=720"),
            # src=("rtspsrc "
            #      "location=rtsp://admin:xxx@192.168.1.137/onvif1"),
            gap=3
        )
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
        self.motion.snapshot(datetime.now().strftime('%Y.%m.%d-%H.%M.%S'))
        self.motion.start_capture(datetime.now().strftime('%Y.%m.%d-%H.%M.%S'))
        self.motion.start_live()

    def on_motion_finished(self, _):
        print("Motion end")
        self.motion.stop_capture()
        self.motion.stop_live()

    def on_eos(self, _):
        self.quit()

    def on_error(self, _, gerror, strerror):
        print("Error:", gerror.message)


if __name__ == '__main__':
    Gst.init([])
    app = App()
    app.run()
