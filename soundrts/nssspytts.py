"""
This module behaves like pyTTS.
It runs on Mac OS X with NSSpeechSynthesizer.
The only behavior provided is the behavior that tts.py needs.
"""

from AppKit import NSSpeechSynthesizer


# not used; provided for compatibility
tts_async = 0
tts_purge_before_speak = 0

_engine = NSSpeechSynthesizer.alloc().init()


class TTS:

    def __init__(self):
        pass
    
    def IsSpeaking(self):
        return _engine.isSpeaking()

    def Speak(self, text, *args):
        _engine.startSpeakingString_(text)

    def Stop(self):
        _engine.stopSpeaking()


def Create():
    return TTS()
