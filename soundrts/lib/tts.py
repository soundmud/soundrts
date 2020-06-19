import queue
import threading
import time

import accessible_output2.outputs.auto

from .log import warning, exception


class _TTS:

    _end_time = None

    def __init__(self, wait_delay_per_character):
        self.o = accessible_output2.outputs.auto.Auto()
        self._wait_delay_per_character = wait_delay_per_character

    def IsSpeaking(self):
        if self._end_time is None:
            return False
        else:
            return self._end_time > time.time()

    def Speak(self, text):
        self.o.output(text, interrupt=True)
        self._end_time = time.time() + len(text) * self._wait_delay_per_character

    def Stop(self):
        self.o.output("", interrupt=True)
        self._end_time = None


_tts = None
_is_speaking = False

_queue = queue.Queue()


def is_speaking():
    return _is_speaking


def _speak(text):
    with _lock:
        try:
            _tts.Speak(text)
        except:
            exception("error during _tts.Speak('%s')", text)


def speak(text):
    global _is_speaking
    assert isinstance(text, str)
    _queue.put((_speak, text))
    _is_speaking = True


def _stop():
    with _lock:
        if _is_speaking:
            try:
                _tts.Stop()
            except:
                pass # speak() will have a similar error and fall back to sounds
    
    
def stop():
    global _is_speaking
    _queue.put((_stop, ))
    _is_speaking = False


def _loop():
    while(True):
        cmd = _queue.get()
        if not _queue.empty():
            #print "skipped!", cmd
            continue
        try:
            cmd[0](*cmd[1:])
        except:
            exception("")


def _loop2():
    global _is_speaking
    while(True):
        if _is_speaking:
            time.sleep(.1)
            with _lock:
                if not _tts.IsSpeaking():
                    _is_speaking = False
        time.sleep(.1)


def init(wait_delay_per_character):
    global _tts, _lock
    _lock = threading.Lock()
    _tts = _TTS(wait_delay_per_character)
    t = threading.Thread(target=_loop)
    t.daemon = True
    t.start()
    t = threading.Thread(target=_loop2)
    t.daemon = True
    t.start()
