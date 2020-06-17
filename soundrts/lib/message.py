import time

from soundrts.lib.screen import screen_subtitle_set
from soundrts.lib.sound import DEFAULT_VOLUME
from soundrts.lib.sound_cache import sounds


def is_text(o):
    return isinstance(o, str)


class Message:

    def __init__(self, list_of_sound_numbers, lv=DEFAULT_VOLUME, rv=DEFAULT_VOLUME, said=False, expiration_delay=45, update_type=None):
        self.list_of_sound_numbers = list_of_sound_numbers
        self.lv = lv
        self.rv = rv
        self.said = said
        self.expiration_time = time.time() + expiration_delay
        self.update_type = update_type

    def has_expired(self):
        return self.expiration_time < time.time()

    def translate_and_collapse(self, remove_sounds=False):
        q = [sounds.translate_sound_number(sn) for sn in self.list_of_sound_numbers]
        result = []
        for i, _ in enumerate(q[:]):
            if remove_sounds and not is_text(q[i]):
                q[i] = None
                continue
            if is_text(q[i]) and i + 1 < len(q) and is_text(q[i + 1]):
                q[i + 1] = q[i] + " " + q[i + 1]
                q[i] = None
        for p in q:
            if p is not None:
                result.append(p)
        return result
    
    def display(self):
        txt = self.translate_and_collapse(remove_sounds=True)
        if txt:
            txt = txt[0]
        else:
            txt = ""
        screen_subtitle_set(txt)
