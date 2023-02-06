"""Sounds and text stored in memory (cache).
Loaded from resources (depending on the active language,
packages, mods, campaign, map)."""
import os
import re
import zipfile
from typing import Dict, Optional, Union

import pygame

from soundrts import parameters
from soundrts.lib.log import warning
from soundrts.lib.msgs import NB_ENCODE_SHIFT

SHORT_SILENCE = "9998"  # 0.01 s
SILENCE = "9999"  # 0.2 s


class Layer:

    txt: Dict[str, str]
    sounds: Dict[str, Union[str, tuple, pygame.mixer.Sound]]

    def __init__(self, res, path=None):
        self.txt = res.load_texts(path)
        self._load_sounds(res, path)
        if path is None:
            # the silent sounds are needed (used as random noises in style.txt)
            self.txt[SHORT_SILENCE] = ","
            self.txt[SILENCE] = "."
        self.path = path

    def _load_sound(self, key, file_ref):
        # if a text exists with the same name, the sound won't be loaded
        if key in self.txt:
            warning("didn't load %s.ogg (text exists)", key)
        elif key not in self.sounds:
            self.sounds[key] = file_ref

    def _load_sounds(self, res, root: Optional[Union[str, zipfile.ZipFile]]):
        self.sounds = {}
        if isinstance(root, zipfile.ZipFile):
            for path in res.get_sound_paths("ui", ""):
                for name in root.namelist():
                    if name.startswith(path) and name.endswith(".ogg"):
                        self._load_sound(os.path.basename(name)[:-4], (root, name))
        else:
            for path in res.get_sound_paths("ui", root):
                if os.path.isdir(path):
                    for dirpath, _, filenames in os.walk(path):
                        for name in filenames:
                            if name.endswith(".ogg"):
                                self._load_sound(name[:-4], os.path.join(dirpath, name))


def _volume(name, path):
    d1 = parameters.d.get("volume", {})
    if d1.get(name) is not None:
        return d1.get(name)
    else:
        d2 = parameters.d.get("default_volume", {})
        for n2, dv in d2.items():
            if n2 in os.path.normpath(path).split(os.sep):
                return dv
    return 1


class Sound(pygame.mixer.Sound):
    def __init__(self, path, name):
        super().__init__(file=path)
        self.name = name
        self.path = path
        self.update_volume()

    def update_volume(self):
        self.set_volume(_volume(self.name, self.path))


class SoundCache:
    """The sound cache contains numbered sounds and texts.
    Usually a number will give only one type of value, but strange things
    can happen (until I fix this), with SHORT_SILENCE and SILENCE for example.
    """

    def __init__(self):
        self.layers = []

    @property
    def cache(self):
        return [
            s
            for layer in self.layers
            for s in layer.sounds.values()
            if hasattr(s, "update_volume")
        ]

    def get_sound(self, name, warn=True):
        """return the sound corresponding to the given name"""
        key = "%s" % name
        for layer in reversed(self.layers):
            if key in layer.sounds:
                s = layer.sounds[key]
                if isinstance(s, str):  # full path of the sound
                    # load the sound now
                    try:
                        layer.sounds[key] = Sound(s, key)
                        return layer.sounds[key]
                    except:
                        warning("couldn't load %s" % s)
                        del layer.sounds[key]
                        continue  # try next layer
                elif isinstance(s, tuple):
                    zip_archive, name = s
                    layer.sounds[key] = pygame.mixer.Sound(file=zip_archive.open(name))
                    return layer.sounds[key]
                else:  # sound
                    return s
        if warn:
            warning("this sound may be missing: %s", name)
        return None

    def has_sound(self, name):
        """return True if the cache have a sound with that name"""
        return self.get_sound(name, warn=False)

    def has_text(self, key):
        """return True if the cache have a text with that name"""
        assert isinstance(key, str)
        for layer in reversed(self.layers):
            if key in layer.txt:
                return True
        return False

    def get_text(self, key):
        """return the text corresponding to the given name"""
        assert isinstance(key, str)
        for layer in reversed(self.layers):
            if key in layer.txt:
                return layer.txt[key]

    def load_default(self, res):
        """load the default layer into memory from res"""
        self.layers = [Layer(res)]

    def load(self, res, path):
        self.layers.append(Layer(res, path))

    def unload(self, path):
        assert self.layers[-1].path == path
        del self.layers[-1]

    def translate_sound_number(self, sound_number):
        """Return the text or sound corresponding to the sound number.

        If the number is greater than NB_ENCODE_SHIFT, then its really a number.
        """
        key = "%s" % sound_number
        if self.has_text(key):
            return self.get_text(key)
        if re.match("^[0-9]+$", key) is not None and int(key) >= NB_ENCODE_SHIFT:
            return "%s" % (int(key) - NB_ENCODE_SHIFT)
        if self.has_sound(key):
            return self.get_sound(key)
        if re.match("^[0-9]+$", key) is not None:
            warning("this sound may be missing: %s", sound_number)
        try:
            return str(key)
        except:
            warning("Unicode error in %s", repr(key))
            return str(key, errors="ignore")

    def update_volumes(self):
        for s in self.cache:
            s.update_volume()


sounds = SoundCache()
