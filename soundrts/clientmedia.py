"""This ugly module is fighting with res.py to make some useful job."""

import os
import platform

import pygame

from . import config
from . import msgparts as mp
from . import res
from .lib.msgs import nb2msg
from .lib.screen import set_screen
from .lib.sound import get_volume, init_sound, set_volume, sound_stop
from .lib.sound_cache import sounds
from .lib.voice import voice
from .version import VERSION

if platform.system() == "Windows":
    # problem with F10 and DirectX, so use windib
    os.environ["SDL_VIDEODRIVER"] = "windib"

fullscreen = False


def update_display_caption():
    """set the window title"""
    pygame.display.set_caption(f"SoundRTS {VERSION} {res.mods} {res.soundpacks}")


def minimal_init():
    """initialize sound, voice, screen, window title, keyboard"""
    init_sound(config.num_channels)
    voice.init(config)
    set_screen(fullscreen)
    update_display_caption()
    pygame.key.set_repeat(500, 100)


def init_media():
    """initialize sound, voice, screen, window title, keyboard,
    and sound cache"""
    minimal_init()
    sounds.load_default(res)


def modify_volume(incr):
    """increase or decrease the main volume, and say it"""
    set_volume(min(1, max(0, get_volume() + 0.1 * incr)))
    sound_stop()
    voice.item(nb2msg(round(get_volume() * 100)) + mp.PERCENT_VOLUME)


def toggle_fullscreen():
    """toggle full screen mode, and say it"""
    global fullscreen
    fullscreen = not fullscreen
    set_screen(fullscreen)
    if fullscreen:
        voice.item(mp.DISPLAY_ON)
    else:
        voice.item(mp.DISPLAY_OFF)


def get_fullscreen():
    """return True if in full screen mode"""
    return fullscreen


def close_media():
    """try to clean up before closing the client"""
    sound_stop()
    pygame.quit()


def play_sequence(names):
    """play a sequence of sounds or texts, each one interruptible"""
    sound_stop()
    for name in names:
        voice.important([name])  # each element is interruptible
