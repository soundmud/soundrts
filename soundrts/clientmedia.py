import os
import platform
import sys
import time

import pygame

from clientmediascreen import *#GraphicConsole
from clientmediasound import *#sounds, sound_pre_init, sound_init, incr_volume, sound_stop, get_volume
from clientmediavoice import *#voice
from msgs import nb2msg
from version import VERSION


if platform.system() == "Windows":
    # problem with F10 and DirectX, so use windib
    os.environ["SDL_VIDEODRIVER"] = "windib"

def init_media():
    init_sound()
    voice.init()
    set_screen(fullscreen)
    pygame.display.set_caption("SoundRTS %s" % VERSION)
    pygame.key.set_repeat()
    sounds.load_default()
    time.sleep(.25) # the first sound is truncated

def modify_volume(incr):
    set_volume(min(1, max(0, get_volume() + .1 * incr)))
    sound_stop()
    voice.item(nb2msg(round(get_volume() * 100)) + [4253])

def toggle_fullscreen():
    global fullscreen
    fullscreen = not fullscreen
    set_screen(fullscreen)
    if fullscreen:
        voice.item([4206])
    else:
        voice.item([4207])

def get_fullscreen():
    return fullscreen

fullscreen = False
