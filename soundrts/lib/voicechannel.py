import time
from typing import Any, List, Tuple

import pygame

from soundrts import version
from soundrts.lib import sound, tts
from soundrts.lib.message import is_text

DEBUG_MODE = version.IS_DEV_VERSION


class VoiceChannel:
    _queue: List[Tuple[Any, float, float]] = []  # sounds of the message currently said
    _starting_time = 0
    _total_duration = 0

    def __init__(self, config=None):
        self.c = pygame.mixer.Channel(0)
        tts.init(config.wait_delay_per_character)

    def play(self, msg):
        if DEBUG_MODE:
            msg.display()
        self.stop()
        for p in msg.translate_and_collapse():
            self._queue.append((p, msg.lv, msg.rv))
        self.update()
        self._starting_time = time.time()

    def is_almost_done(self):
        duration = time.time() - self._starting_time
        if duration > 1:  # >1s
            return True
        else:
            return False

    def stop(self):
        self.c.stop()  # interrupt
        tts.stop()
        self._queue = []

    def update(self):
        if not self.c.get_busy() and not tts.is_speaking():
            if self._queue:
                self._play_next_msg_part()

    def _play_next_msg_part(self):
        s, lv, rv = self._queue.pop(0)
        if is_text(s):
            tts.speak(s)
        else:
            self._play(s, lv, rv)

    def get_busy(self):
        return (
            self.c.get_busy()
            or self._queue
            or (self.c.get_queue() is not None)
            or tts.is_speaking()
        )

    def _play(self, s, lv, rv):
        # note: set_volume() doesn't seem to work with queued sounds
        v = sound.main_volume * sound.voice_volume
        self.c.set_volume(lv * v, rv * v)
        self.c.play(s)
        self.c.set_endevent(pygame.locals.USEREVENT)
