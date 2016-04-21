"""SoundRTS resource manager"""

import os

from lib.resource import ResourceLoader
import config
import options
from paths import MAPS_PATHS


def get_all_packages_paths():
    """return the default "maps and mods" paths followed by the paths of the active packages"""
    return MAPS_PATHS # + package_manager.get_packages_paths()

if options.mods is not None:
    mods = options.mods
else:
    mods = config.mods
_r = ResourceLoader(mods, config.soundpacks, get_all_packages_paths())
mods = _r.mods
soundpacks = _r.soundpacks
get_text_file = _r.get_text_file
load_texts = _r.load_texts
load_sounds = _r.load_sounds


def on_loading():
    from lib.voice import voice
    voice.item([4322, mods, "."])  # "loading"


def on_complete():
    from lib.voice import voice
    for mod in _r.unavailable_mods:
        voice.alert([1029, 4330, mod])


def reload_all():
    global mods, soundpacks
    from clientmedia import sounds, update_display_caption
    _r.update_mods_list(mods, soundpacks, get_all_packages_paths())
    mods = _r.mods
    soundpacks = _r.soundpacks
    update_display_caption()
    sounds.load_default(_r, on_loading, on_complete)


def set_mods(new_mods):
    global mods
    if new_mods != mods:
        mods = new_mods
        reload_all()


# campaigns


def _get_campaigns():
    from campaign import Campaign
    w = []
    for mp in get_all_packages_paths():
        d = os.path.join(mp, "single")
        if os.path.isdir(d):
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if os.path.isdir(p):
                    if n == "campaign":
                        w.append(Campaign(p, [4267]))
                    else:
                        w.append(Campaign(p))
    return w


_campaigns = None
_mods_at_the_previous_campaigns_update = None


def campaigns():
    global _campaigns, _mods_at_the_previous_campaigns_update
    if _campaigns is None or _mods_at_the_previous_campaigns_update != mods:
        _campaigns = _get_campaigns()
        _mods_at_the_previous_campaigns_update = mods
    return _campaigns


# multiplayer maps


def _add_official_multi(w):
    from mapfile import Map
    maps = [line.strip().split() for line in open("cfg/official_maps.txt")]
    for n, digest in maps:
        p = os.path.join("multi", n)
        w.append(Map(p, digest, official=True))


def _add_custom_multi(w):
    from mapfile import Map
    for mp in get_all_packages_paths():
        d = os.path.join(mp, "multi")
        if os.path.isdir(d):
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if os.path.normpath(p) not in (os.path.normpath(x.path) for x in w):
                    w.append(Map(p, None))


def _move_recommended_maps(w):
    from definitions import Style
    style = Style()
    style.load(get_text_file("ui/style", append=True, localize=True))
    for n in reversed(style.get("parameters", "recommended_maps")):
        for m in reversed(w[:]): # reversed so the custom map is after the official map
            if m.get_name()[:-4] == n:
                w.remove(m)
                w.insert(0, m)


def _get_worlds_multi():
    w = []
    _add_official_multi(w)
    _add_custom_multi(w)
    _move_recommended_maps(w)
    return w


_multi_maps = None
_mods_at_the_previous_multi_maps_update = None


def worlds_multi():
    global _multi_maps, _mods_at_the_previous_multi_maps_update
    if _multi_maps is None or _mods_at_the_previous_multi_maps_update != mods:
        _multi_maps = _get_worlds_multi()
        _mods_at_the_previous_multi_maps_update = mods
    return _multi_maps


# mods


def is_a_soundpack(path):
    for name in ("rules.txt", "ai.txt"):
        if os.path.isfile(os.path.join(path, name)):
            return False
    return True


def is_a_mod(path):
    return not is_a_soundpack(path)


def available_mods(check_mod_type=is_a_mod):
    result = []
    for path in get_all_packages_paths():
        mods_path = os.path.join(path, "mods")
        for mod in os.listdir(mods_path):
            path = os.path.join(mods_path, mod)
            if os.path.isdir(path) \
               and check_mod_type(path) \
               and mod not in result:
                result.append(mod)
    return result


def available_soundpacks():
    return available_mods(is_a_soundpack)