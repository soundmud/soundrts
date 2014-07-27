import os
import platform
import time

from clientmediascreen import *
from clientmediasound import *
from clientmediavoice import *
from msgs import nb2msg
from version import VERSION
import g


if platform.system() == "Windows":
    # problem with F10 and DirectX, so use windib
    os.environ["SDL_VIDEODRIVER"] = "windib"


class LowLevelInterface(object):

    def __init__(self, mixer_freq):
        self.set_pygame(mixer_freq)
        g.text_screen = sys.stderr = sys.stdout = GraphicConsole()
        sounds.load_default()
        time.sleep(.25) # the first sound is truncated

    def set_pygame(self, mixer_freq):
        sound_pre_init(mixer_freq)
        pygame.init()
        sound_init()
        voice.init()
        self.set_display()
        pygame.key.set_repeat()

    def set_display(self):
        try:
            g.screen = pygame.display.set_mode(g.DISPLAY_RES)
        except:
            g.screen = pygame.display.set_mode()
        pygame.display.set_caption("SoundRTS %s" % VERSION)


def init_media(*args):
    LowLevelInterface(*args)

def modify_volume(incr=1):
    incr_volume(incr)
    sound_stop()
    voice.item(nb2msg(round(get_volume() * 100)) + [4253])
