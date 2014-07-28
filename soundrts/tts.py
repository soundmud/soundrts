import platform
import time

import config
from version import VERSION


if platform.system() == "Windows":
    if config.srapi == 0:
        try:
            import win32compytts as pyTTS
        except:
            print "Couldn't use SAPI."
    else:
        try:
            import srapipytts as pyTTS
        except:
            print "Couldn't use ScreenReaderAPI."
elif platform.system() == "Linux":
    try:
        import linuxpytts as pyTTS
    except:
        print "Couldn't use Speech Dispatcher."
elif platform.system() == "Darwin":
    try:
        import nssspytts as pyTTS
    except:
        print "Couldn't use Appkit.NSSpeechSynthesizer."

from lib.log import *


MINIMAL_PLAYING_TIME = 1 # in seconds
TTS_TIMEOUT = .1 # in seconds

_tts = None
_tts_previous_start_time = 0

def warn_if_slow(f):
    if VERSION.endswith("-dev"):
        def new_f(*args, **keywords):
            t = time.time()
            r = f(*args, **keywords)
            if time.time() - t  >= .1:
                warning("%s took %s seconds!", f.__name__, time.time() - t)
            return r
    else:
        new_f = f
    return new_f

@warn_if_slow
def is_speaking():
    if not is_available: return False
    # The TTS doesn't always start speaking at once, but we don't want to wait.
    # So we consider that the TTS is speaking during the first milliseconds,
    # even if _tts.IsSpeaking() returns False.
    return _tts.IsSpeaking() or time.time() < _tts_previous_start_time + TTS_TIMEOUT

@warn_if_slow
def speak(text):
    assert isinstance(text, unicode)
    global _tts_previous_start_time
    if not is_available: return
    try:
        _tts.Speak(text, pyTTS.tts_async, pyTTS.tts_purge_before_speak)
    except:
        exception("error during tts_speak('%s'): back to recorded speech", text)
    _tts_previous_start_time = time.time()

@warn_if_slow
def stop():
    if not is_available: return
    global _tts_previous_start_time
    if _tts_previous_start_time:
        try:
            _tts.Stop()
        except:
            pass # speak() will have a similar error and fall back to sounds
    _tts_previous_start_time = 0

def init():
    global _tts, is_available
    try:
        _tts = pyTTS.Create()
    except:
        is_available = False
    else:
        is_available = True

init()
