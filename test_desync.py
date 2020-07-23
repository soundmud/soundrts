#! .venv\Scripts\python.exe
import sys
from multiprocessing import Process
import os
import time

try:
    import win32gui
except ModuleNotFoundError:
    pass

from soundrts import config
config.mods = "crazymod9beta10"

from soundrts import worldplayercomputer2 as wpc2
from soundrts.lib.nofloat import PRECISION


class Computer2ForTests(wpc2.Computer2):

    def cheat(self):
        self.has = lambda x: True
        self.resources = [1000 * PRECISION for _ in self.resources]

    _play = wpc2.Computer2.play

    def play(self):
        self.cheat()
        self._play()


wpc2.Computer2 = Computer2ForTests  # type: ignore

from soundrts.lib.voice import voice
from soundrts import clientmain
from soundrts.game import MultiplayerGame
from soundrts import servermain
from soundrts import world


def do_nothing(*a, **k):
    pass

def remove_voice():
    voice._say_now = do_nothing
    voice.item = do_nothing
    voice.info = do_nothing

MultiplayerGame._countdown = do_nothing   # type: ignore

def set_position(x, y):
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"

def run_client(n, auto):
    if 0:#n == 0:
        world.PROFILE = True
    if 1:#n != 0:
        remove_voice()
    set_position(0, n * 235 + 50)
    clientmain.init_media()
    clientmain.connect_and_play(auto=auto)

def run_server():
    if "win32gui" in sys.modules:
        hwnd = win32gui.GetForegroundWindow()
        win32gui.MoveWindow(hwnd, 400, 0, 800, 800, True)
    servermain.start_server(parameters="no_metaserver")


class Create:

    def __init__(self, map_index, speed, public=""):
        self.map_index = map_index
        self.speed = speed
        self.public = public

    def run(self, menu):
        menu.push(f"create {self.map_index} {self.speed} {self.public}")
        return True


class Invite:

    def __init__(self, nb):
        self.nb = nb

    def run(self, menu):
        if getattr(menu, "available_players", False):
            menu.push("invite %s" % menu.available_players[0])
            self.nb -= 1
            if self.nb == 0:
                return True


class InviteAI:

    def __init__(self, easy=0, aggressive=0, ai2=0):
        self.easy = easy
        self.aggressive = aggressive
        self.ai2 = ai2

    def run(self, menu):
        for _ in range(self.easy):
            menu.push("invite_easy")
            time.sleep(.1)
        for _ in range(self.aggressive):
            menu.push("invite_aggressive")
            time.sleep(.1)
        for _ in range(self.ai2):
            menu.push("invite_ai2")
            time.sleep(.1)
        return True


class Register:

    def run(self, menu):
        if menu.invitations:
            menu.push("register %s" % menu.invitations[0][0])
            return True


class Start:

    def run(self, menu):
        if len(menu.registered_players) >= menu.map.nb_players_min:
            menu.push("start")
            return True


if __name__ == "__main__":
    n = 1
    Process(target=run_server).start()
    ais = (0, 1, 10)
    # ais = (1, 1, 10)
    # map_index = 10
    map_index = "jl4"
    Process(target=run_client, args=(0, [Create(map_index, 20), Invite(n), InviteAI(*ais), Start()], )).start()
    for i in range(n):
        Process(target=run_client, args=(i + 1, [Register()], )).start()
