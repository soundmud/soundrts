"""The resources are usually stored on a disk (as opposed to memory).
Which resource will be loaded will depend on the preferred language,
the active packages, the loading order of the mods.
Some resources will be combined differently: some are replaced (sounds),
some are merged (some text files).
"""

import locale
import os

import pygame

from soundrts.lib import encoding
from soundrts.lib.log import warning


TXT_FILE = "ui/tts"


def localize_path(path, lang):
    """Return the path modified for this language.
    For example, "ui" becomes "ui-fr".
    """
    head, tail = os.path.split(path)
    if tail == "ui":
        return os.path.join(head, tail + "-" + lang)
    else:
        sub_head, sub_tail = os.path.split(head)
        if sub_tail == "ui":
            return os.path.join(sub_head, sub_tail + "-" + lang, tail)
        else:
            return path


def best_language_match(lang, available_languages):
    """Return the available language matching best the preferred language."""
    if lang is None:
        lang = ""
    # full match
    lang = lang.replace("_", "-")
    for available_language in available_languages:
        if lang.lower() == available_language.lower():
            return available_language
    # ignore the second part
    if "-" in lang:
        lang = lang.split("-")[0]
    # match a short code
    for available_language in available_languages:
        if lang.lower() == available_language.lower():
            return available_language
    # match a long code
    for available_language in available_languages:
        if "-" in available_language:
            shortened_code = available_language.split("-")[0]
            if lang.lower() == shortened_code.lower():
                return available_language
    # default value
    return "en"


class ResourceLoader(object):
    """Load resources.
    Depends on language, active packages, loading order of the mods.
    Ideally, it should only care about folders and files.
    """
    def __init__(self, mods, soundpacks, all_packages_paths, base_path="res"):
        self._paths = []
        self.base_path = base_path
        self.update_mods_list(mods, soundpacks, all_packages_paths)
        self.language = self._get_language()

    def _available_languages(self):
        """Return a list of available languages.
        Guessed from the existing "ui-language" folders.
        """
        result = ["en"]
        for path in self._paths:
            for name in os.listdir(path):
                if name.startswith("ui-") and name[3:] not in result:
                    result.append(name[3:])
        return result

    def _get_language(self):
        """guess and return the best language for this situation"""
        cfg = open("cfg/language.txt").read().strip()
        if cfg:
            lang = cfg
        else:
            try:
                lang = locale.getdefaultlocale()[0]
            except ValueError:
                lang = "en"
                warning("Couldn't get the system language. "
                        "To use another language, edit 'cfg/language.txt' "
                        "and write 'pl' for example.")
        return best_language_match(lang, self._available_languages())

    def _update_paths(self, all_packages_paths, mods):
        actual_mods = []
        unavailable_mods = []
        for mod_name in mods.split(","):
            mod_name = mod_name.strip()
            if mod_name:
                mod_found = False
                # all_packages_paths is reversed so the latest path
                # takes precedence over the previous ones.
                for root in reversed(all_packages_paths):
                    path = os.path.join(root, "mods", mod_name)
                    if os.path.exists(path):
                        self._paths.append(path)
                        mod_found = True
                        break
                if not mod_found:
                    unavailable_mods.append(mod_name)
                else:
                    actual_mods.append(mod_name)
        return ",".join(actual_mods), unavailable_mods

    def update_mods_list(self, mods, soundpacks, all_packages_paths):
        """Update the paths list, ignoring unavailable mods.
        
        mods: load order of the mods
        all_packages_paths: load order of the packages 
        """
        self._paths = []
        self._paths.append(self.base_path)  # vanilla path
        self.mods, self.unavailable_mods = self._update_paths(all_packages_paths, mods)
        self.soundpacks, self.unavailable_soundpacks = self._update_paths(all_packages_paths, soundpacks)

    def _localized_paths(self, path, localize):
        """Return the paths according to the preferred language.
        The default language is always returned as a fallback.
        """
        result = [path]
        if localize and self.language:
            result.append(localize_path(path, self.language))
        return result

    def _get_text_files(self, name, localize=False, root=None):
        """Return a list of text files contents.
        """
        name += ".txt"
        if root is None:
            roots = self._paths
        else:
            roots = [root]
        result = []
        for root in roots:
            for text_file_path in self._localized_paths(os.path.join(root, name), localize):
                if os.path.isfile(text_file_path):
                    result.append(open(text_file_path, "rU").read())
        return result

    def get_text_file(self, name, localize=False, append=False, root=None):
        """Return the content of the text file with the highest priority
        or the concatenation of the text files contents.
        """
        if append:
            return "\n".join(self._get_text_files(name, localize, root))
        else:
            return self._get_text_files(name, localize, root)[-1]

    def load_texts(self, root=None):
        """load and return a dictionary of texts
        
        Args:
            root (str): the path of the root
            
        Returns:
            dict: texts
        """
        result = {}
        for txt in self._get_text_files(TXT_FILE, localize=True, root=root):
            lines = txt.split("\n")
            encoding_name = encoding.encoding(txt)
            for line in lines:
                try:
                    line = line.strip()
                    if line:
                        key, value = line.split(None, 1)
                        if value:
                            try:
                                value = unicode(value, encoding_name)
                            except ValueError:
                                value = unicode(value, encoding_name, "replace")
                                warning("in '%s', encoding error: %s", TXT_FILE, line)
                            result[key] = value
                        else:
                            warning("in '%s', line ignored: %s", TXT_FILE, line)
                except:
                    warning("in '%s', syntax error: %s", TXT_FILE, line)
        return result

    def _get_sound_paths(self, path, root=None):
        """Return the list of sound paths.
        Depends on the load order of the mods and the preferred language.
        The list is reversed so the most relevant paths appear first.
        """
        if root is None:
            roots = self._paths
        else:
            roots = [root]
        result = []
        for root in roots:
            result.extend(self._localized_paths(os.path.join(root, path), True))
        return reversed(result)

    def _load_sound_if_needed(self, filename, root, dest, sound_is_not_needed):
        """load the sound to the dictionary
        If a text exists for the sound number, the sound won't be loaded."""
        if filename[-4:] == ".ogg":
            key = filename[:-4]
            if sound_is_not_needed(key):
                warning("didn't load %s (text exists)", filename)
                return
            if key not in dest:
                full_path = os.path.join(root, filename)
                try:
                    dest[key] = pygame.mixer.Sound(full_path)
                except:
                    warning("couldn't load %s" % full_path)

    def load_sounds(self, root, dest, sound_is_not_needed):
        """load the sounds to the dictionary
        If a text exists with the same name, the sound won't be loaded."""
        for path in self._get_sound_paths("ui", root):
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for filename in files:
                        self._load_sound_if_needed(filename, root, dest, sound_is_not_needed)
