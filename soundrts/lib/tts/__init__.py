from __future__ import print_function
from builtins import str
import platform
import queue
import threading
import time

from ..log import warning, exception


pyTTS = None
TTS_TIMEOUT = .1 # in seconds

_tts = None
_is_speaking = False

_queue = queue.Queue()


def is_speaking():
    if not is_available: return False
    # The TTS doesn't always start speaking at once, but we don't want to wait.
    # So we consider that the TTS is speaking during the first milliseconds,
    # even if _tts.IsSpeaking() returns False.
    return _is_speaking
#    with _lock:
#        return _tts.IsSpeaking() or time.time() < _tts_previous_start_time + TTS_TIMEOUT


def _speak(text):
    with _lock:
        try:
            _tts.Speak(text, pyTTS.tts_async, pyTTS.tts_purge_before_speak)
        except:
            exception("error during tts_speak('%s'): back to recorded speech", text)


def speak(text):
    global _is_speaking
    assert isinstance(text, str)
    if not is_available: return
    _queue.put((_speak, text))
    _is_speaking = True


def _stop():
    with _lock:
        if _is_speaking:
            try:
                _tts.Stop()
            except:
                pass # speak() will have a similar error and fall back to sounds
#         else:
#             print "no stop"
    
    
def stop():
    global _is_speaking
    if not is_available: return
    _queue.put((_stop, ))
    _is_speaking = False


def loop():
    while(True):
        cmd = _queue.get()
        if not _queue.empty():
            #print "skipped!", cmd
            continue
        try:
            cmd[0](*cmd[1:])
        except:
            exception("")


def loop2():
    global _is_speaking
    while(True):
        if _is_speaking:
            time.sleep(TTS_TIMEOUT)
            with _lock:
                if not _tts.IsSpeaking():
                    _is_speaking = False
        time.sleep(.1)


def init(jaws=0, srapi=1, srapi_wait=.1):
    global _tts, is_available, _lock, pyTTS
    if platform.system() == "Windows":
        if jaws == 1:
            try:
                from . import windows_jaws as pyTTS
            except:
                print("Couldn't use Jaws.")
        elif srapi == 0:
            try:
                from . import windows_sapi5 as pyTTS
            except:
                print("Couldn't use SAPI.")
        else:
            try:
                from . import windows_srapi as pyTTS
                pyTTS.srapi_wait = srapi_wait
            except:
                print("Couldn't use ScreenReaderAPI.")
    elif platform.system() == "Linux":
        try:
            from . import linux as pyTTS
        except:
            print("Couldn't use Speech Dispatcher.")
    elif platform.system() == "Darwin":
        try:
            from . import darwin as pyTTS
        except:
            print("Couldn't use Appkit.NSSpeechSynthesizer.")
    _lock = threading.Lock()
    try:
        _tts = pyTTS.Create()
    except:
        is_available = False
    else:
        is_available = True
        t = threading.Thread(target=loop)
        t.daemon = True
        t.start()
        t = threading.Thread(target=loop2)
        t.daemon = True
        t.start()


def close():
    if not is_available: return
    # speech dispatcher must be closed or the program won't close
    if hasattr(_tts, "_client"):
        _tts._client.close()
