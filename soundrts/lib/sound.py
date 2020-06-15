from __future__ import division
from builtins import object
from builtins import range
import math
import random
import time

import pygame

from .log import warning
from soundrts.lib import tts


DEFAULT_VOLUME = math.sin(math.pi / 4.0) # (about .7) volume for each speaker for a "in front of you" message


def distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

def angle(x1, y1, x2, y2, o=0):
    """angle of x2,y2 related to player x1,y1,o"""
    d = distance(x1, y1, x2, y2)
    if d == 0:
        return 0 # object too close => in front of player
    ac = math.acos((x2 - x1) / d)
    if y2 - y1 > 0:
        a = ac
    else:
        a = - ac
    return a - math.radians(o)

def vision_stereo(x, y, xo, yo, o, volume=1): # no distance
    vg, vd = stereo(x, y, xo, yo, o, volume, True)
    if max(vg, vd) < .2: # never silent
        vg, vd = .2, .2
    return vg, vd

def stereo(x, y, xo, yo, o, volume=1, vision=False):
    a = angle(x, y, xo, yo, o)
    d = distance(x, y, xo, yo)
    vg = (math.sin(a) + 1) / 2.0
    vd = 1 - vg
    vg = math.sin(vg * math.pi / 2.0)
    vd = math.sin(vd * math.pi / 2.0)
    if math.cos(a) < 0: # behind
        if vision:
            k = 1.3
        else:
            k = 2.0 # TODO: attenuate less? (especially in overhead view)
        vg /= k
        vd /= k
    if d < 1 or vision:
        d = 1
    vg = min(vg * volume / d, 1)
    vd = min(vd * volume / d, 1)
    return vg, vd

def find_idle_channel():
    # because pygame.mixer.find_channel() doesn't work
    # (it can return the reserved channel 0)
    for n in range(1, pygame.mixer.get_num_channels()): # avoid channel 0
        if not pygame.mixer.Channel(n).get_busy():
            return pygame.mixer.Channel(n)


class SoundManager(object):

    soundsources = []
    soundtime = {}

    def remember_starttime(self, sound):
        self.soundtime[sound] = time.time()

    def should_be_played(self, sound, limit):
        return self.soundtime.get(sound, 0) + limit < time.time()
#        return self.soundtime.get(sound, 0) + sound.get_length() * .1 \
#                                                               < time.time()

    def find_a_channel(self, priority):
        c = find_idle_channel()
        if c is None:
            playing = [s for s in self.soundsources
                       if s.is_playing() and s.priority < priority]
            if playing:
                playing = sorted(playing, key=lambda x: (x.priority,
                                                         max(x.previous_vol)))
                c = playing[0].channel
                c.stop()
                return c
        else:
            if c.get_endevent() == pygame.locals.USEREVENT:
                warning("find_channel() have chosen the reserved channel!")
            return c

    def set_listener(self, listener):
        self.listener = listener

    def get_stereo_volume(self, source):
        if self.listener.immersion:
            flattening_factor = 1.0
        else:
            flattening_factor = 2.0 # TODO: calc this
            self.listener.o = 90
        return stereo(self.listener.x, self.listener.y / flattening_factor,
                      source.x, source.y / flattening_factor,
                      self.listener.o, source.v)

    def play(self, *args, **keywords):
        s = SoundSource(*args, **keywords)
        if s.is_playing():
            self.soundsources.append(s)
            return s

    def play_loop(self, *args, **keywords):
        s = LoopingSoundSource(*args, **keywords)
        if not s.has_stopped:
            self.soundsources.append(s)
            return s

    def play_stereo(self, s, vol=1, limit=0):
        """play a stereo sound (not a positional sound)"""
        if s is not None:
            if not self.should_be_played(s, limit):
                return
            c = self.find_a_channel(priority=10)
#            if c is None:
#                warning("couldn't find a sound channel with priority<10")
##                pygame.mixer.find_channel(True).stop()
            if c is not None:
                c.play(s)
                if isinstance(vol, tuple):
                    c.set_volume(vol[0] * volume, vol[1] * volume)
                else:
                    c.set_volume(vol * volume)
                self.remember_starttime(s)

    def update(self):
        for s in self.soundsources[:]:
            s.update()
            if s.has_stopped:
                self.soundsources.remove(s)

    def stop(self):
        for s in self.soundsources:
            s.stop()


psounds = SoundManager() # psounds = positional sounds (3D)


class _SoundSource(object):

    channel = None
    previous_vol = (0, 0)
    has_stopped = False

    def __init__(self, s, v, x, y, priority, limit=0, ambient=False):
        self.sound = s
        self.v = v
        self.x = x
        self.y = y
        self.priority = priority
        self.ambient = ambient
        if self.sound is None:
            self.has_stopped = True
        elif psounds.should_be_played(self.sound, limit):
            self._start()

    def _start(self):
        if not self._volume_too_low():
            self.channel = psounds.find_a_channel(self.priority)
            if self.channel is not None:
                self.channel.play(self.sound, self.loop)
                self.channel.set_endevent(pygame.locals.USEREVENT + 1)
                self._update_volume(force=True)
        if self.is_playing():
            psounds.remember_starttime(self.sound)

    def is_playing(self):
        return self.channel is not None and self.channel.get_busy() and \
               self.channel.get_sound() == self.sound

    def _volume_too_low(self):
        return max(psounds.get_stereo_volume(self)) < .02

    def _update_volume(self, force=False):
        if self._volume_too_low():
            self.channel.stop()
            self.channel = None
        else:
            if self.ambient:
                vol = self.ambient_volume()
            else:
                vol = psounds.get_stereo_volume(self)
            if force or vol != self.previous_vol:
                self.channel.set_volume(vol[0] * volume, vol[1] * volume)
                self.previous_vol = vol

    def move(self, x, y):
        if self.has_stopped:
            return
        if (x, y) != (self.x, self.y):
            self.x = x
            self.y = y
            self.update()

    def stop(self):
        if self.is_playing():
            self.channel.stop()
            self.channel = None
        self.has_stopped = True


class SoundSource(_SoundSource):

    loop = 0

    def update(self):
        if self.has_stopped:
            return
        if self.is_playing():
            self._update_volume()
        else:
            self.stop()

    def ambient_volume(self):
##                r = random.random()
##                vol = (r, 1 - r)
        return random.random(), random.random()


class LoopingSoundSource(_SoundSource):

    loop = -1

    def update(self):
        if self.has_stopped:
            return
        if self.is_playing():
            self._update_volume()
        else:
            self._start()

    def ambient_volume(self):
        return 1, 1


def sound_stop(stop_voice_too=True):
    psounds.stop()
    if stop_voice_too:
        pygame.mixer.stop()
        tts.stop()
    else: # stop every channel except channel 0 (voice channel)
        for _id in range(1, pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(_id).stop()
        

volume = .5


def get_volume():
    return volume


def set_volume(v):
    global volume
    volume = v


voice_volume = 1.0


def init_sound(num_channels):
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    pygame.mixer.set_reserved(1)
    pygame.mixer.set_num_channels(num_channels)
