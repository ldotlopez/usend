#!/usr/bin/env python3

import ipdb


from aiy import (
    voicehat,
    audio,
    i18n,
)
import speech_recognition as sr


def trace():
    ipdb.set_trace()
    pass


class App:
    def __init__(self):
        i18n.set_language_code('es-ES')

        self.button = voicehat.get_button()
        self.ui = voicehat.get_status_ui()
        self.ui.status('starting')

        self.sr = sr.Recognizer()

        self._run = False

    def run(self):

        self._run = True
        while self._run:
            self.ui.status('ready')
            self.button.wait_for_press()
            self.ui.status('listening')

            audio.say('Dime')
            with sr.Microphone(0) as source:
                input_audio = self.sr.listen(source)
                self.ui.status('thinking')
                try:
                    text = self.sr.recognize_google(input_audio, language='es')
                except sr.UnknownValueError:
                    audio.say('No he entendido una mierda')
                    continue
                if text == 'adiós':
                    self.stop()
                    audio.say('Ale, que te den')
                else:
                    audio.say('Tu has dicho: ' + text)
                    print("=>", text)
                    # trace()

    def stop(self):
        self._run = False

if __name__ == '__main__':
    App().run()
