"""Sounds and text stored in memory (cache).
Loaded from resources (depending on the active language,
packages, mods, campaign, map)."""

import re

from soundrts.lib.log import warning
from soundrts.lib.msgs import NB_ENCODE_SHIFT


SHORT_SILENCE = "9998"  # 0.01 s
SILENCE = "9999"  # 0.2 s


class Layer(object):

    def __init__(self):
        self.sounds = {}
        self.txt = {}


class SoundCache(object):
    """The sound cache contains numbered sounds and texts.
    Usually a number will give only one type of value, but strange things
    can happen (until I fix this), with SHORT_SILENCE and SILENCE for example.
    The cache contains a maximum of three layers: default, campaign and map.
    """
    default = Layer()
    campaign = Layer()
    map = Layer()

    @property
    def layers(self):
        return (self.map, self.campaign, self.default)

    def get_sound(self, name, warn=True):
        """return the sound corresponding to the given name"""
        key = "%s" % name
        for layer in self.layers:
            if key in layer.sounds:
                return layer.sounds[key]
        if warn:
            warning("this sound may be missing: %s", name)
        return None

    def has_sound(self, name):
        """return True if the cache have a sound with that name"""
        return self.get_sound(name, warn=False)

    def has_text(self, key):
        """return True if the cache have a text with that name"""
        assert isinstance(key, str)
        for layer in self.layers:
            if key in layer.txt:
                return True
        return False

    def sound_is_not_needed(self, key):
        # the silent sounds are needed (used as random noises in style.txt)
        return self.has_text(key) and key not in [SHORT_SILENCE, SILENCE]

    def get_text(self, key):
        """return the text corresponding to the given name"""
        assert isinstance(key, str)
        for layer in self.layers:
            if key in layer.txt:
                return layer.txt[key]

    def _add_special_values(self):
        """add some values not defined in text files"""
        self.default.txt[SHORT_SILENCE] = u","
        self.default.txt[SILENCE] = u"."

    def load_default(self, res, on_loading=None, on_complete=None):
        """load the default layer into memory from res"""
        self.default.sounds = {}
        self.default.txt = res.load_texts()
        self._add_special_values()
        if on_loading:
            on_loading()
        res.load_sounds(None, self.default.sounds, self.sound_is_not_needed)
        if on_complete:
            on_complete()

    def enter_campaign(self, res, path):
        """load the campaign layer into memory from res and campaign path"""
        self.campaign.txt = res.load_texts(path)
        res.load_sounds(path, self.campaign.sounds, self.sound_is_not_needed)

    def exit_campaign(self):
        """unload the campaign layer"""
        self.campaign = Layer()

    def enter_map(self, res, path):
        """load the map layer into memory from res and map path"""
        if path is None:
            return
        self.map.txt = res.load_texts(path)
        res.load_sounds(path, self.map.sounds, self.sound_is_not_needed)

    def exit_map(self):
        """unload the map layer"""
        self.map = Layer()

    def translate_sound_number(self, sound_number):
        """Return the text or sound corresponding to the sound number.

        If the number is greater than NB_ENCODE_SHIFT, then its really a number.
        """
        key = "%s" % sound_number
        if self.has_text(key):
            return self.get_text(key)
        if re.match("^[0-9]+$", key) is not None and int(key) >= NB_ENCODE_SHIFT:
            return u"%s" % (int(key) - NB_ENCODE_SHIFT)
        if self.has_sound(key):
            return self.get_sound(key)
        if re.match("^[0-9]+$", key) is not None:
            warning("this sound may be missing: %s", sound_number)
        return unicode(key)


sounds = SoundCache()
