"""Sounds and text stored in memory (cache).
Loaded from resources (depending on the active language,
packages, mods, campaign, map)."""
import re
import zipfile
from pathlib import Path
from typing import Dict, Optional, Union

import pygame

from soundrts import parameters
from soundrts.lib.log import warning
from soundrts.lib.msgs import NB_ENCODE_SHIFT

TXT_FILE = "ui/tts"

SHORT_SILENCE = "9998"  # 0.01 s
SILENCE = "9999"  # 0.2 s


class TextTable(dict):
    def __init__(self, res, path):
        super().__init__()
        for txt in res.texts(TXT_FILE, localize=True, root=path):
            self._update_from_text(txt)

    def _update_from_text(self, txt):
        lines = txt.split("\n")
        for line in lines:
            line = line.strip()
            if line:
                try:
                    key, value = line.split(None, 1)
                except ValueError:
                    warning("in '%s', syntax error: %s", TXT_FILE, line)
                else:
                    if value:
                        self[key] = value
                    else:
                        warning("in '%s', line ignored: %s", TXT_FILE, line)


class Layer:
    sounds: Dict[str, Union[str, tuple, pygame.mixer.Sound]]

    def __init__(self, res, path=None):
        self.txt = TextTable(res, path)
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
        for package, path in reversed(list(res.paths("ui", root, localize=True))):
            for name in package.relative_paths_of_files_in_subtree(path):
                n = Path(name)
                if n.suffix == ".ogg":
                    key = n.stem
                    file_ref = package, name
                    self._load_sound(key, file_ref)


def _volume(name, mod_name):
    d1 = parameters.d.get("volume", {})
    if d1.get(name) is not None:
        return d1.get(name)
    else:
        d2 = parameters.d.get("default_volume", {})
        if d2.get(mod_name) is not None:
            return d2.get(mod_name)
    return 1


class Sound(pygame.mixer.Sound):
    def __init__(self, file, mod_name, name):
        super().__init__(file=file)
        self.name = name
        self.mod_name = mod_name
        self.update_volume()

    def update_volume(self):
        self.set_volume(_volume(self.name, self.mod_name))


class SoundCache:
    """Numbered sounds and texts.
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
                if isinstance(s, Sound):
                    return s
                else:
                    package, name = s
                    mod_name = package.name
                    try:
                        layer.sounds[key] = Sound(package.open_binary(name), mod_name, key)
                        return layer.sounds[key]
                    except IOError:
                        warning("couldn't load %s from %s", s, mod_name)
                        del layer.sounds[key]
                        continue  # try next layer
        if warn:
            warning("this sound may be missing: %s", name)
        return None

    def has_sound(self, name):
        """return True if the cache have a sound with that name"""
        try:
            return self.get_sound(name, warn=False)
        except pygame.error:
            pass

    def text(self, key):
        """return the text corresponding to the given name"""
        assert isinstance(key, str)
        for layer in reversed(self.layers):
            if key in layer.txt:
                return layer.txt[key]

    def load_default(self, res):
        """load the default layer into memory from res"""
        self.layers = [Layer(res)]

    def translate_sound_number(self, sound_number):
        """Return the text or sound corresponding to the sound number.

        If the number is greater than NB_ENCODE_SHIFT, then it's really a number.
        """
        key = "%s" % sound_number
        if self.text(key) is not None:
            return self.text(key)
        if re.match("^[0-9]+$", key) is not None and int(key) >= NB_ENCODE_SHIFT:
            return "%s" % (int(key) - NB_ENCODE_SHIFT)
        if self.has_sound(key):
            return self.get_sound(key)
        if re.match("^[0-9]+$", key) is not None:
            warning("this sound may be missing: %s", sound_number)
        try:
            return str(key)
        except ValueError:
            warning("Unicode error in %s", repr(key))
            return str(key, errors="ignore")

    def update_volumes(self):
        for s in self.cache:
            s.update_volume()


sounds = SoundCache()
