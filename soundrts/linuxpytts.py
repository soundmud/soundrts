"""
This module behaves like pyTTS. It runs on Linux.
The only behavior provided is the behavior that tts.py needs.
"""

import speechd  # @UnresolvedImport


# not used; provided for compatibility
tts_async = 0
tts_purge_before_speak = 0


class TTS(object):

    _is_speaking = False

    def __init__(self):
        self._client = speechd.SSIPClient("")

    def IsSpeaking(self):
        return self._is_speaking

    def _callback(self, callback_type):
        if callback_type == speechd.CallbackType.BEGIN:
            self._is_speaking = True
        elif callback_type == speechd.CallbackType.END:
            self._is_speaking = False
        elif callback_type == speechd.CallbackType.CANCEL:
            self._is_speaking = False

    def Speak(self, text, *args):
        self._client.speak(text, callback=self._callback,
                           event_types=(speechd.CallbackType.BEGIN,
                                        speechd.CallbackType.CANCEL,
                                        speechd.CallbackType.END))

    def Stop(self):
        self._client.stop()


def Create():
    return TTS()
