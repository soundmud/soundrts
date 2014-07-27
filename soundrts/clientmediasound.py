import math
import random
import re
import string
import sys
import time

import pygame
from pygame.locals import *

from lib.log import *

from clientmediascreen import FONT
import encoding
import res
import tts


DEFAULT_VOLUME = math.sin(math.pi / 4.0) # (about .7) volume for each speaker for a "in front of you" message

def translate_ns(s):
    s = "%s" % s
    if sounds.is_text(s):
        return sounds.get_text(s)
    if re.match("^[0-9]+$", s) is not None and int(s) >= 1000000:
        return u"%s" % (int(s) - 1000000)
    if sounds.get_sound(s):
        return sounds.get_sound(s)
    if re.match("^[0-9]+$", s) is not None:
        warning("this sound may be missing: %s", s)
    return unicode(s)

def is_text(o):
    return isinstance(o, unicode)

def translate_and_collapse_lns(lns, remove_sounds=False):
    q = [translate_ns(ns) for ns in lns]
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

def display(lns):
    from version import VERSION
    if VERSION[-4:] != "-dev": return # don't show ugly orthography
    import g
    txt = translate_and_collapse_lns(lns, remove_sounds=True)
    if txt:
        txt = txt[0]
    else:
        txt = ""
    if g.game:
        g.subtitle = txt
    else:
        ren = FONT.render(txt, 1, (200, 200, 200))
        g.screen.fill((0, 0, 0))
        g.screen.blit(ren, (0, 0))
        pygame.display.flip()

TXT_FILE = "ui/tts"

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
    for n in xrange(1, pygame.mixer.get_num_channels()): # avoid channel 0
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

    def update(self):
        for s in self.soundsources[:]:
            s.update()
            if s.has_stopped:
                self.soundsources.remove(s)

    def stop(self):
        for s in self.soundsources:
            s.stop()


psounds = SoundManager() # psounds = positionned sounds (3D)


class _SoundSource(object):

    channel = None
    previous_vol = (0, 0)
    has_stopped = False

    def __init__(self, s, v, x, y, priority, limit=0, ambient=False):
        self.sound = sounds.get_sound(s)
        self.v = v
        self.x = x
        self.y = y
        self.priority = priority
        self.ambient = ambient
        if self.sound is None:
            warning("this sound may be missing: %s", s)
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
        return max(psounds.get_stereo_volume(self)) < .02 # volume less than
                                                          # 2 per cent

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


class VoiceChannel(object):

    _queue = [] # sounds of the message currently said
    _starting_time = 0
    _total_duration = 0

    def __init__(self):
        self.c = pygame.mixer.Channel(0)

    def _tts_play(self, lns, lv, rv):
        self.stop()
        if (lv, rv) != (DEFAULT_VOLUME, DEFAULT_VOLUME):
            self._queue.append([sounds.get_sound("1003"), lv, rv])
        r = translate_and_collapse_lns(lns)
        for p in r:
            self._queue.append([p, lv, rv])
        self.update()
        self._starting_time = time.time()

    def play(self, lns, lv, rv):
        self._tts_play(lns, lv, rv)
        display(lns)

    def is_almost_done(self):
        duration = time.time() - self._starting_time
        if duration > 1: # >1s
            return True
        else:
            return False

    def stop(self):
        self.c.stop() # interrompre
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
        return self.c.get_busy() or self._queue or (self.c.get_queue() != None) \
               or tts.is_speaking()

    def _play(self, s, lv, rv):
        # note: set_volume() doesn't seem to work with queued sounds
        v = volume * voice_volume
        self.c.set_volume(lv * v, rv * v)
        self.c.play(s)
        self.c.set_endevent(pygame.locals.USEREVENT)

    def _spell(self, s):
        ls = []
        s = ("%s" % s).lower()
        for c in s:
            if c in string.digits:
                k = string.digits.index(c) + 3000
            elif c in string.ascii_lowercase:
                k = string.ascii_lowercase.index(c) + 5000
            else:
                continue
            ls.append(k)
#            ls.append(9998)
        return ls


def sound_pre_init(mixer_freq):
    if mixer_freq == 44100 and sys.platform == "win32":
        # increase buffer to avoid scratchy sounds
        pygame.mixer.pre_init(mixer_freq, -16, 2, 1024 * 3)
    else:
        pygame.mixer.pre_init(mixer_freq)

def sound_init():
    pygame.mixer.set_reserved(1)

def sound_stop(stop_voice_too=True):
    psounds.stop()
    if stop_voice_too:
        pygame.mixer.stop()
        tts.stop()
    else: # stop every channel except channel 0 (voice channel)
        for _id in range(1, pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(_id).stop()


class SoundCache(object):

    default_sounds = {}
    default_txt = {}
    campaign_sounds = {}
    campaign_txt = {}
    campaign_path = None
    map_sounds = {}
    map_txt = {}

    def get_sound(self, name):
        name = "%s" % name
        for d in [self.map_sounds, self.campaign_sounds, self.default_sounds]:
            if name in d:
                return d[name]
        return None

    def play(self, name, vol=1, limit=0):
        s = self.get_sound(name)
        if s is not None:
            if not psounds.should_be_played(s, limit):
                return
            c = psounds.find_a_channel(priority=10)
#            if c is None:
#                warning("couldn't find a sound channel with priority<10")
##                pygame.mixer.find_channel(True).stop()
            if c is not None:
                c.play(s)
                if isinstance(vol, tuple):
                    c.set_volume(vol[0] * volume, vol[1] * volume)
                else:
                    c.set_volume(vol * volume)
                psounds.remember_starttime(s)
        else:
            warning("couldn't find sound %s", name)

    def is_text(self, s):
        for d in (self.map_txt, self.campaign_txt, self.default_txt):
            if s in d:
                return True
        return False

    def get_text(self, s):
        for d in (self.map_txt, self.campaign_txt, self.default_txt):
            if s in d:
                return d[s]

    def _load(self, path, d):
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for n in files:
                    if n[-4:] == ".ogg":
                        k = n[:-4]
                        if self.is_text(k) and \
                           k not in ["9998", "9999"]:
                            continue
                        if k not in d:
                            p = os.path.join(root, n)
                            try:
                                d[k] = pygame.mixer.Sound(p)
                            except:
                                warning("couldn't load %s" % p)

    def load_default(self):
        self.default_txt = _read_txt()
        for path in res.get_sound_paths("ui"):
            self._load(path, self.default_sounds)

    def enter_campaign(self, path):
        if self.campaign_path != path:
            self.campaign_txt = _read_txt(path)
            self.campaign_path = path
            for p in res.get_sound_paths("ui", root=path):
                self._load(p, self.campaign_sounds)

    def exit_campaign(self):
        self.campaign_path = None
        self.campaign_sounds = {}
        self.campaign_txt = {}

    def enter_map(self, path):
        if path is None: return
        self.map_txt = _read_txt(path)
        for p in res.get_sound_paths("ui", root=path):
            self._load(p, self.map_sounds)

    def exit_map(self):
        self.map_sounds = {}
        self.map_txt = {}
        
    def play_sequence(self, names):
        from clientmediavoice import voice # outsourcing the job...
        sound_stop()
        for name in names:
            voice.important([name]) # each element is interruptible


def _incr_value(v, incr):
    return min(1, max(0, v + .1 * incr))

volume = .5

def get_volume():
    return volume

def incr_volume(incr):
    global volume
    volume = _incr_value(volume, incr)

voice_volume = 1.0

def get_voice_volume():
    return voice_volume

def incr_voice_volume(incr):
    global voice_volume
    voice_volume = _incr_value(voice_volume, incr)

def _read_txt(root=None):
    path = TXT_FILE
    result = {}
    for txt in res.get_texts(path, locale=True, root=root):
        lines = txt.split("\n")
        encoding_name = encoding.encoding(txt)
        for line in lines:
            try:
                line = line.strip()
                if line:
                    k, v = line.split(None, 1)
                    if v:
                        try:
                            v = unicode(v, encoding_name)
                        except ValueError:
                            v = unicode(v, encoding_name, "replace")
                            warning("in '%s', encoding error: %s", path, line)
                        result[k] = v
                    else:
                        warning("in '%s', line ignored: %s", path, line)
            except:
                warning("in '%s', syntax error: %s", path, line)
    result["9998"] = u","
    result["9999"] = u"."
    return result

sounds = SoundCache()
