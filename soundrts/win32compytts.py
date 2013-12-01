"""
This module behaves like pyTTS.
It runs on Windows with win32com and SAPI 5.
The only behavior provided is the behavior that tts.py needs.
"""

import win32com.client


_engine = win32com.client.Dispatch('SAPI.SpVoice')
tts_async = 1
tts_purge_before_speak = 2


class TTS:

    def __init__(self):
        pass
    
    def IsSpeaking(self):
        return _engine.Status.RunningState != 1

    def Speak(self, text, *args):
        _engine.Speak(text, sum(args))

    def Stop(self):
        self.Speak(u"", tts_async, tts_purge_before_speak)


def Create():
    return TTS()
