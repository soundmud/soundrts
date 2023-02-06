#! .venv\Scripts\python.exe
import logging
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import random
import sys
import time
from multiprocessing import Process

try:
    import win32gui
except ModuleNotFoundError:
    pass

from soundrts import worldplayercomputer2 as wpc2, clientgame, version
from soundrts.lib.nofloat import PRECISION
from soundrts import clientmain, res, servermain, world
from soundrts.game import MultiplayerGame, TrainingGame
from soundrts.lib import sound
from soundrts.lib.voice import voice
from soundrts.mapfile import worlds_multi
from soundrts.clientgame import GameInterface
from soundrts.clientmain import restore_game


version.IS_DEV_VERSION = True
clientgame.IS_DEV_VERSION = True
import pytest  # exceptions will be reraised by log.exception()
LOGGING_LEVEL = logging.ERROR


class Computer2ForTests(wpc2.Computer2):
    def cheat(self):
        self.has = lambda x: True
        self.resources = [1000 * PRECISION for _ in self.resources]

    _play = wpc2.Computer2.play

    def play(self):
        self.cheat()
        self._play()


wpc2.Computer2 = Computer2ForTests  # type: ignore
if 0:  # test all orders
    wpc2.orders = sorted(ORDERS_DICT.keys())  # sort to avoid desync


def do_nothing(*a, **k):
    pass


def remove_voice():
    voice._say_now = do_nothing
    voice.item = do_nothing
    voice.info = do_nothing


MultiplayerGame._countdown = do_nothing  # type: ignore


def set_position(x, y):
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"


def run_single(n, auto, mods, m):
    import logging
    from soundrts.lib import log
    log.clear_handlers()
    log.add_console_handler(LOGGING_LEVEL)

    remove_voice()
    res.set_mods(mods)
    set_position(205, n * 235 + 50)
    clientmain.init_media()
    t = TrainingGame(m, ["test", "easy"], ["random_faction", "random_faction"], ["1", "2"])
    t.auto = auto
    t.run()


def restore_single(n, auto):
    import logging
    from soundrts.lib import log
    log.clear_handlers()
    log.add_console_handler(LOGGING_LEVEL)

    remove_voice()
    set_position(205, n * 235 + 50)
    clientmain.init_media()
    TrainingGame.auto = auto
    restore_game()


def run_client(n, auto, mods):
    import logging
    from soundrts.lib import log
    log.clear_handlers()
    log.add_console_handler(LOGGING_LEVEL)

    if 0:  # n == 0:
        world.PROFILE = True
    if 1:  # n != 0:
        remove_voice()
    res.set_mods(mods)
    set_position(0, n * 235 + 50)
    clientmain.init_media()
    clientmain.connect_and_play(auto=auto)


def run_server():
    import logging
    from soundrts.lib import log
    log.clear_handlers()
    log.add_console_handler(logging.CRITICAL)

    if "win32gui" in sys.modules and "PYCHARM_HOSTED" not in os.environ:
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
        if self.nb == 0:
            return True
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
            time.sleep(0.1)
        for _ in range(self.aggressive):
            menu.push("invite_aggressive")
            time.sleep(0.1)
        for _ in range(self.ai2):
            menu.push("invite_ai2")
            time.sleep(0.1)
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


class PressRandomKeys:
    def __init__(self, dt):
        self.dt = dt
        self._next_time = time.time() + dt

    def run(self, interface: GameInterface):
        sound.main_volume = 0
        if not isinstance(interface, GameInterface):
            return True
        if self._next_time <= time.time():
            cmd, args = random.choice(list(interface._bindings._bindings.values()))
            if cmd.__name__[4:] not in ["game_menu", "say", "console", "fullscreen", "gamemenu", "toggle_tick"]:
                # print(cmd.__name__, " ".join(args))
                cmd(*args)
                self._next_time = time.time() + self.dt


class Wait:
    def __init__(self, t):
        self.end = time.time() + t

    def run(self, interface):
        return self.end <= time.time()


class Save:
    def run(self, interface):
        print("save")
        interface.gm_save()
        return True


class Restore:
    def run(self, interface):
        print("restore")
        interface.gm_restore()
        return True


def game_session():
    import logging
    from soundrts.lib import log
    log.clear_handlers()
    log.add_console_handler(LOGGING_LEVEL)

    print("*********************************************************")

    _mods = random.choice(["", "crazymod9beta10", "aoe", "starwars", "blitzkrieg", "modern"])
    res.set_mods(_mods)

    maps = [m for m in worlds_multi() if m.official]
    m = random.choice(maps)

    n_guests_max = random.randint(0, 2)
    creator_plus_one_ai = 2
    n = min(max(m.nb_players_max - creator_plus_one_ai, 0), n_guests_max)
    ais = random.choice([(0, 1, 10), (1, 1, 10), (1, 0, 10), (0, 0, 10)])

    print("mod(s):", _mods)
    print("map:", m.path, "for", m.nb_players_max, "players max")
    print("clients:", n + 1)
    print("local AIs:", m.nb_players_max - n - 1, "from", ais)
    print()

    lp = []

    # game creator
    p = Process(
        target=run_client,
        args=(0, [Create(m.path, 20), Invite(n), InviteAI(*ais), Start(), PressRandomKeys(.1)], _mods),
    )
    p.start()
    lp.append(p)

    # game guests
    for i in range(n):
        p = Process(target=run_client, args=(i + 1, [Register(), Wait(3), PressRandomKeys(.1)], _mods))
        p.start()
        lp.append(p)

    # single player save
    p = Process(target=run_single, args=(0, [Wait(3), Save(), PressRandomKeys(.5)], _mods, m))
    p.start()
    lp.append(p)

    # single player restore
    p = Process(target=restore_single, args=(1, [PressRandomKeys(.5)]))
    p.start()
    lp.append(p)

    time.sleep(45)

    for p in lp:
        p.terminate()


if __name__ == "__main__":
    Process(target=run_server).start()
    while True:
        game_session()

# TODO: try many game types, replay, languages
