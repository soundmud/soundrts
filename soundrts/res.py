"""SoundRTS resource manager"""

import os

from . import config, options
from .lib.resource import ResourceLoader
from .paths import MAPS_PATHS


def get_all_packages_paths():
    """return the default "maps and mods" paths followed by the paths of the active packages"""
    return MAPS_PATHS  # + package_manager.get_packages_paths()


if options.mods is not None:
    mods = options.mods
else:
    mods = config.mods
_r = ResourceLoader(mods, config.soundpacks, get_all_packages_paths())
mods = _r.mods
soundpacks = _r.soundpacks
get_text_file = _r.get_text_file
load_texts = _r.load_texts
get_sound_paths = _r.get_sound_paths


def reload_all():
    global mods, soundpacks
    from .clientmedia import sounds, update_display_caption

    _r.update_mods_list(mods, soundpacks, get_all_packages_paths())
    mods = _r.mods
    soundpacks = _r.soundpacks
    update_display_caption()
    sounds.load_default(_r)


def set_mods(new_mods):
    global mods
    if new_mods != mods:
        mods = new_mods
        reload_all()


def set_soundpacks(new_soundpacks):
    global soundpacks
    if new_soundpacks != soundpacks:
        soundpacks = new_soundpacks
        reload_all()


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
            if os.path.isdir(path) and check_mod_type(path) and mod not in result:
                result.append(mod)
    return result


def available_soundpacks():
    return available_mods(is_a_soundpack)
