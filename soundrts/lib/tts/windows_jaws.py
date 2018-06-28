"""
This module behaves like pyTTS.
It runs on Windows with win32com and Jaws.
The only behavior provided is the behavior that tts.py needs.
"""

import win32com.client
import time


srapi_wait = .1

_jaws = win32com.client.Dispatch('FreedomSci.JawsApi')
tts_async = 1
tts_purge_before_speak = 2


class TTS(object):

    _end_time = None

    def IsSpeaking(self):
        if self._end_time is None:
            return False
        else:
            return self._end_time > time.time()

    def Speak(self, text, *args):
        _jaws.SayString(text)
        self._end_time = time.time() + len(text) * srapi_wait

    def Stop(self):
        _jaws.StopSpeech()
        self._end_time = None


def Create():
    return TTS()
