"""Which resource will be loaded will depend on the preferred language,
the active packages, the loading order of the mods.
Some resources will be combined differently: some are replaced (sounds),
some are merged (some text files).
"""
import locale
import os
import re
from pathlib import Path
from typing import List

from soundrts.definitions import rules, load_ai, style
from soundrts.lib.log import warning, exception
from soundrts.lib.package import PackageStack, Package
from soundrts.lib.sound_cache import sounds
from .. import config, options
from ..mapfile import Map
from ..pack import unpack_file
from ..paths import BASE_PACKAGE_PATH, packages_paths, DOWNLOADED_PATH


def localized_path(path, lang):
    """Return the path modified for this language.
    For example, "ui" becomes "ui-fr".
    """
    return re.sub(r"(?<!\w)ui(?!\w)", "ui-" + lang, path)


def localized_paths(path, language):
    """Return the paths according to the preferred language.
    The default language is always returned as a fallback.
    """
    result = [path]
    if language:
        result.append(localized_path(path, language))
    return result


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


def _preferred_language():
    try:
        with open("cfg/language.txt") as t:
            cfg = t.read().strip()
    except IOError:
        warning("couldn't read cfg/language.txt")
        return "en"
    if cfg:
        return cfg
    else:
        try:
            return locale.getdefaultlocale()[0]
        except ValueError:
            warning(
                "Couldn't get the system language. "
                "To use another language, edit 'cfg/language.txt' "
                "and write 'pl' for example."
            )
            return "en"


preferred_language = _preferred_language()


class ResourceStack:
    mods = ""
    soundpacks = ""
    _campaign = None
    _map = None
    language = "en"

    def __init__(self, base_and_additional_packages_paths):
        self.packages = PackageStack(base_and_additional_packages_paths)
        self._reload()

    def update_packages(self):
        self.__init__([BASE_PACKAGE_PATH] + packages_paths())

    def available_mods(self):
        return [mod.name for mod in self.packages.mods() if not mod.is_a_soundpack()]

    def available_soundpacks(self):
        return [mod.name for mod in self.packages.mods() if mod.is_a_soundpack()]

    def _available_languages(self):
        """Guessed from the existing "ui-language" folders."""
        result = {"en"}
        prefix = "ui-"
        for package in self._layers:
            for name in package.dirnames():
                if name.startswith(prefix):
                    result.add(name[len(prefix):])
        return result

    def _best_available_language(self):
        return best_language_match(preferred_language, self._available_languages())

    def _add_layers(self, packages, mods):
        actual_mods = []
        self._actual_mods_and_required_mods = set()
        for mod_name in [name.strip() for name in mods.split(",")]:
            if mod_name:
                mod = packages.mod(mod_name)
                if mod:
                    self._add_layer(mod, packages)
                    actual_mods.append(mod_name)
        return ",".join(actual_mods)

    def _add_layer(self, mod, packages):
        self._actual_mods_and_required_mods.add(mod.name)
        for required_mod_name in getattr(mod, "mods", []):
            if required_mod_name not in self._actual_mods_and_required_mods:
                required_mod = packages.mod(required_mod_name)
                if required_mod:
                    self._add_layer(required_mod, packages)
        self._layers.append(mod)

    def _add(self, package):
        if package:
            self._layers.append(package)

    _notify = None

    def register(self, f):
        self._notify = f
        self._notify()

    _previous_layers = None

    def _reload(self):
        self._layers = self.packages[:1]
        self.mods = self._add_layers(self.packages, self.mods)
        self.soundpacks = self._add_layers(self.packages, self.soundpacks)
        if self._campaign:
            self._add(self._campaign.resources)
        if self._map:
            self._add(self._map.resources)
        if self._layers != self._previous_layers:
            self.language = self._best_available_language()
            self.load_rules_and_ai()
            self.load_style()
            sounds.load_default(self)
            if self._notify:
                self._notify()
            self._previous_layers = self._layers[:]

    def set_mods(self, new_mods):
        if new_mods != self.mods:
            self.mods = new_mods
            self._reload()

    def set_soundpacks(self, new_soundpacks):
        if new_soundpacks != self.soundpacks:
            self.soundpacks = new_soundpacks
            self._reload()

    def set_map(self, m=None):
        self._map = m
        self._reload()

    def set_campaign(self, c=None):
        self._campaign = c
        self._reload()

    def load_rules_and_ai(self):
        rules.load(self.text("rules", append=True))
        load_ai(self.text("ai", append=True))

    def load_style(self):
        style.load(self.text("ui/style", append=True, localize=True))

    def texts(self, name: str, localize=False, root=None) -> List[str]:
        result = []
        for package, path in self.paths(name + ".txt", root, localize):
            try:
                with package.open_text(path) as file:
                    text = file.read()
            except (FileNotFoundError, KeyError):
                pass
            else:
                result.append(text)
        return result

    def text(self, name, localize=False, append=False, root=None):
        """Return the content of the text file with the highest priority
        or the concatenation of the text files contents.
        """
        texts = self.texts(name, localize, root)
        if append:
            return "\n".join(texts)
        else:
            return texts[-1]

    def paths(self, path, root=None, localize=False):
        if root is None:
            roots = self._layers
        else:
            roots = [root]
        if localize:
            lang = self.language
        else:
            lang = None
        for root in roots:
            for p in localized_paths(path, lang):
                yield root, p

    _multi_maps = None
    _mods_at_the_previous_multi_maps_update = None

    def multiplayer_maps(self):
        if self._multi_maps is None or self._mods_at_the_previous_multi_maps_update != self.mods:
            self._reload()  # required by test_desync (used by _move_recommended_maps)
            self._multi_maps = _get_multi_maps()
            self._mods_at_the_previous_multi_maps_update = self.mods
        return self._multi_maps

    def find_multiplayer_map(self, digest):
        for m in self.multiplayer_maps():
            if m.digest() == digest:
                return m

    def unpack_map(self, b: bytes, save=False):
        buffer, name = unpack_file(b)
        m = Map.loads(buffer, name)
        if save and not self.find_multiplayer_map(m.digest()):
            filename = Path(name).stem + "_" + m.digest()[:8] + Path(name).suffix
            _save_downloaded_map(buffer, filename)
            self._multi_maps = None  # update soon
        return m

    _campaigns = None
    _mods_at_the_previous_campaigns_update = None

    def campaigns(self):
        if self._campaigns is None or self._mods_at_the_previous_campaigns_update != self.mods:
            self._campaigns = _campaigns()
            _mods_at_the_previous_campaigns_update = self.mods
        return self._campaigns

    def find_campaign(self, name):
        for c in self.campaigns():
            if c.name == name:
                return c


def _campaigns():
    from soundrts.campaign import Campaign
    campaigns = []
    for package in res.packages:
        single = package.subpackage("single")
        if single:
            for n in single.dirnames():
                c = Campaign(single.subpackage(n), n)
                campaigns.append(c)
    return campaigns


def _map_size(m):
    return m.size()


def official_multiplayer_maps():
    maps = []
    official = res.packages[0].subpackage("multi")
    for n in official.filenames():
        m = Map.load(official.open_binary(n), n)
        m.official = True
        maps.append(m)
    return maps


def _add_custom_multi(maps):
    for package in res.packages[1:] + [Package.from_path(DOWNLOADED_PATH)]:
        multi = package.subpackage("multi")
        if multi:
            for n in list(multi.filenames()) + list(multi.dirnames()):
                try:
                    m = Map.load(multi.open_binary(n), n)
                except Exception as e:
                    exception("couldn't load map %s: %s", n, e)
                else:
                    m.title.insert(0, 1097)  # heal sound to alert player
                    maps.append(m)


def _copy_recommended_maps(maps):
    for n in reversed(style.get("parameters", "recommended_maps")):
        for m in reversed(maps[:]):  # reversed so the custom map is after the official map
            if m.name == n:
                maps.insert(0, m)


def _get_multi_maps():
    maps = []
    maps.extend(official_multiplayer_maps())
    _add_custom_multi(maps)
    from .message import Message
    maps.sort(key=lambda x: Message(x.title).translate_and_collapse(remove_sounds=True))
    _copy_recommended_maps(maps)
    return maps


def _save_downloaded_map(b, name):
    try:
        with open(os.path.join(DOWNLOADED_PATH, "multi", name), "wb") as f:
            f.write(b)
    except IOError:
        warning("couldn't write %s", name)


def _resource_stack():
    if options.mods is not None:
        mods = options.mods
    else:
        mods = config.mods
    if options.soundpacks is not None:
        soundpacks = options.soundpacks
    else:
        soundpacks = config.soundpacks

    result = ResourceStack([BASE_PACKAGE_PATH] + packages_paths())
    result.set_mods(mods)
    result.set_soundpacks(soundpacks)

    return result


res = _resource_stack()
