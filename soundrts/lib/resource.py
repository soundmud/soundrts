"""The resources are usually stored on a disk (as opposed to memory).
Which resource will be loaded will depend on the preferred language,
the active packages, the loading order of the mods.
Some resources will be combined differently: some are replaced (sounds),
some are merged (some text files).
"""
import io
import locale
import os
import re
import zipfile
from typing import Dict, List, Optional, Union

from soundrts.lib import encoding
from soundrts.lib.log import warning

TXT_FILE = "ui/tts"


def localize_path(path, lang):
    """Return the path modified for this language.
    For example, "ui" becomes "ui-fr".
    """
    return re.sub(r"(?<!\w)ui(?!\w)", "ui-" + lang, path)


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


with open("cfg/language.txt") as t:
    _cfg = t.read().strip()
if _cfg:
    preferred_language: Optional[str] = _cfg
else:
    try:
        preferred_language = locale.getdefaultlocale()[0]
    except ValueError:
        preferred_language = "en"
        warning(
            "Couldn't get the system language. "
            "To use another language, edit 'cfg/language.txt' "
            "and write 'pl' for example."
        )


class ResourceLoader:
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
        return best_language_match(preferred_language, self._available_languages())

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
        self.soundpacks, self.unavailable_soundpacks = self._update_paths(
            all_packages_paths, soundpacks
        )

    def _localized_paths(self, path, localize):
        """Return the paths according to the preferred language.
        The default language is always returned as a fallback.
        """
        result = [path]
        if localize and self.language:
            result.append(localize_path(path, self.language))
        return result

    def _get_text_files(self, name: str, localize=False, root=None) -> List[str]:
        name += ".txt"
        if root is None:
            roots = self._paths
        else:
            roots = [root]
        result = []
        for root in roots:
            if isinstance(root, zipfile.ZipFile):
                for text_file_path in self._localized_paths(name, localize):
                    if text_file_path in root.namelist():
                        with root.open(text_file_path) as b:
                            e = encoding.encoding(b.read(), text_file_path)
                        with root.open(text_file_path) as b:
                            w = io.TextIOWrapper(b, encoding=e, errors="replace")  # type: ignore
                            result.append(w.read())
            else:
                for text_file_path in self._localized_paths(
                    os.path.join(root, name), localize
                ):
                    if os.path.isfile(text_file_path):
                        with open(text_file_path, "rb") as b:
                            e = encoding.encoding(b.read(), text_file_path)
                        with open(text_file_path, encoding=e, errors="replace") as t:
                            result.append(t.read())
        return result

    def get_text_file(self, name, localize=False, append=False, root=None):
        """Return the content of the text file with the highest priority
        or the concatenation of the text files contents.
        """
        if append:
            return "\n".join(self._get_text_files(name, localize, root))
        else:
            return self._get_text_files(name, localize, root)[-1]

    def load_texts(
        self, root: Optional[Union[str, zipfile.ZipFile]] = None
    ) -> Dict[str, str]:
        result = {}
        for txt in self._get_text_files(TXT_FILE, localize=True, root=root):
            lines = txt.split("\n")
            for line in lines:
                try:
                    line = line.strip()
                    if line:
                        key, value = line.split(None, 1)
                        if value:
                            result[key] = value
                        else:
                            warning("in '%s', line ignored: %s", TXT_FILE, line)
                except:
                    warning("in '%s', syntax error: %s", TXT_FILE, line)
        return result

    def get_sound_paths(self, path, root=None):
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
