"""
This module behaves like pyTTS.
It runs on Windows with ScreenReaderAPI and SAPI5.
The only behavior provided is the behavior that tts.py needs.
"""

import ctypes
import win32com.client
import psutil
import time

# Initialize JAWS screenreader
try:
    _jaws = win32com.client.Dispatch('FreedomSci.JawsApi')
except:
    _jaws = None

# Initialize NVDA screenreader
try:
    _nvda = ctypes.windll.nvdaControllerClient
except:
    _nvda = None

# Initialize Window-Eyes screenreader
try:
    _windowEyes = win32com.client.Dispatch('GWSpeak.Speak')
except:
    _windowEyes = None

# Initialize Windows SpeechAPI
try:
    _sapi5 = win32com.client.Dispatch('SAPI.SpVoice')
except:
    _sapi5 = None

srapi = 1
srapi_wait = .1

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
        self.Stop()
        screenreaderSay = False
        if srapi:
            if _jaws and _jaws.SayString(text):
                screenreaderSay = True
            elif _nvda and not _nvda.nvdaController_speakText(text):
                screenreaderSay = True
            elif _windowEyes:
                # Check the running Window-eyes
                for proc in psutil.process_iter():
                    if proc.name() == 'wineyes.exe':
                        _windowEyes.SpeakString(text)
                        screenreaderSay = True
                        break
        if not screenreaderSay:
            _sapi5.Speak(text, sum(args))
        self._end_time = time.time() + len(text) * srapi_wait

    def Stop(self):
        if _jaws:
            _jaws.StopSpeech()
        if _nvda:
            _nvda.nvdaController_cancelSpeech()
        if _windowEyes:
            _windowEyes.Silence()
        if _sapi5:
            _sapi5.Speak(u'', tts_async + tts_purge_before_speak)
        self._end_time = None


def Create():
    return TTS()
