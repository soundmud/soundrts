import time
import random

from soundrts import parameters
from soundrts.lib.sound import psounds
from soundrts.lib.sound_cache import sounds


class _Noise:
    _source = None

    def __init__(self, obj, style):
        self.obj = obj
        self.style = style

    def stop(self):
        if self._source:
            self._source.stop()


class LoopNoise(_Noise):
    def __init__(self, obj, style):
        super().__init__(obj, style)
        _, self._sound, self.volume, self.ambient = style

    def update(self):
        if self._source and not self._source.ended:
            volume = self.volume
            if self.obj.fow:
                volume *= parameters.d.get("fog_of_war_factor", 0.5)
            self._source.v = volume
            self._source.move(self.obj.x, self.obj.y)
        else:
            volume = self.volume
            if self.obj.fow:
                volume *= parameters.d.get("fog_of_war_factor", 0.5)
            self._source = psounds.play_loop(
                sounds.get_sound(self._sound),
                volume,
                self.obj.x,
                self.obj.y,
                -10,
                # same priority level as "footstep", to avoid unpleasant interruptions (for EntityView at least)
            )


class RepeatNoise(_Noise):
    _next = None

    def __init__(self, obj, style):
        super().__init__(obj, style)
        _, self._interval, self._sounds, self.ambient = style

    def update(self):
        if self._next is None:
            self._next = time.time() + random.random() * self._interval
        # don't start a new "repeat sound" if the previous "repeat sound" hasn't stopped yet
        elif time.time() > self._next and getattr(self._source, "ended", True):
            volume = 1
            if self.obj.fow:
                volume *= parameters.d.get("fog_of_war_factor", 0.5)
            self._source = psounds.play(
                sounds.get_sound(random.choice(self._sounds)),
                volume,
                self.obj.x,
                self.obj.y,
                -20,
                0,
                self.ambient,
            )
            self._next = time.time() + self._interval * (0.8 + random.random() * 0.4)


def noise(obj, style):
    if style:
        if style[0] == "loop":
            return LoopNoise(obj, style)
        if style[0] == "repeat":
            return RepeatNoise(obj, style)
