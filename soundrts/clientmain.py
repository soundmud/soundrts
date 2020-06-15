from __future__ import absolute_import
from builtins import zip
from builtins import object
from . import config
config.load()

from .lib import log
from .lib.log import exception, warning
from .version import VERSION_FOR_BUG_REPORTS
from .paths import CLIENT_LOG_PATH
log.set_version(VERSION_FOR_BUG_REPORTS)
log.add_secure_file_handler(CLIENT_LOG_PATH, "w")
log.add_http_handler("http://jlpo.free.fr/soundrts/metaserver")
log.add_console_handler()

import locale
try:
    locale.setlocale(locale.LC_ALL, '')
except:
    warning("couldn't set locale")

import os
from os.path import join
import pickle
import sys
import tempfile
import time
import webbrowser

from .campaign import campaigns
from .clientmedia import voice, init_media, close_media
from .clientmenu import Menu, input_string, CLOSE_MENU
from .clientserver import connect_and_play, start_server_and_connect
from .clientversion import revision_checker
from .definitions import style
from .game import TrainingGame, ReplayGame
from .lib.msgs import nb2msg
from .lib.resource import best_language_match, preferred_language
from .mapfile import worlds_multi
from .metaserver import servers_list
from . import msgparts as mp
from .paths import CONFIG_DIR_PATH, REPLAYS_PATH, SAVE_PATH
from . import res
from . import stats
from .version import VERSION


def choose_server_ip_in_a_list():
    servers = servers_list(voice)
    total = 0
    compatible = 0
    menu = Menu()
    for s in servers:
        try:
            _, ip, version, login, port = s.split()
        except ValueError:
            warning("line not recognized from the metaserver: %s", s)
        else:
            total += 1
            if version == VERSION:
                compatible += 1
                menu.append([login], (connect_and_play, ip, port),
                            mp.SERVER_HOSTED_BY + [login])
    menu.title = nb2msg(compatible) + mp.SERVERS_ON + nb2msg(total) + mp.ARE_COMPATIBLE
    menu.append(mp.CANCEL2, None, mp.GO_BACK_TO_PREVIOUS_MENU)
    menu.run()

def enter_server_ip():
    host = input_string([], "^[A-Za-z0-9\.]$")
    if host:
        connect_and_play(host)

def multiplayer_menu():
    if config.login == "player":
        voice.alert(mp.ENTER_NEW_LOGIN)
        modify_login()
    menu = Menu(mp.MAKE_A_SELECTION, [
        (mp.CHOOSE_SERVER_IN_LIST, choose_server_ip_in_a_list),
        (mp.ENTER_SERVER_IP, enter_server_ip),
        (mp.CANCEL, None),
         ])
    menu.run()

def replay(n):
    ReplayGame(os.path.join(REPLAYS_PATH, n)).run()

def replay_menu():
    menu = Menu(mp.OBSERVE_RECORDED_GAME)
    for n in sorted(os.listdir(REPLAYS_PATH), reverse=True):
        if n.endswith(".txt"):
            menu.append([time.strftime("%c", time.localtime(int(n[:-4])))],
                        (replay, n))
    menu.append(mp.QUIT2, None)
    menu.run()

def modify_login():
    login = input_string(mp.ENTER_NEW_LOGIN + mp.USE_LETTERS_AND_NUMBERS_ONLY,
                         "^[a-zA-Z0-9]$")
    if login == None:
        voice.alert(mp.CURRENT_LOGIN_KEPT)
    elif (len(login) < 1) or (len(login) > 20):
        voice.alert(mp.BAD_LOGIN + mp.CURRENT_LOGIN_KEPT)
    else:
        voice.alert(mp.NEW_LOGIN + [login])
        config.login = login
        config.save()

def restore_game():
    n = SAVE_PATH
    if not os.path.exists(n):
        voice.alert(mp.BEEP)
        return
    f = open(n)
    try:
        i = int(stats.Stats(None, None)._get_weak_user_id())
        j = int(f.readline())
    except:
        i = 0
        j = "error"
    if i == j:
        try:
            game_session = pickle.load(f)
        except:
            exception("cannot load savegame file")
            voice.alert(mp.BEEP)
            return
        game_session.run_on()
    else:
        warning("savegame file is not from this machine")
        voice.alert(mp.BEEP)

def open_user_folder():
    webbrowser.open(CONFIG_DIR_PATH)


class TrainingMenu(object):

    def _add_ai(self, ai_type):
        self._players.append(ai_type)
        self._factions.append("random_faction")
        self._players_menu.update_menu(self._build_players_menu())

    def _run_game(self):
        TrainingGame(self._map, self._players, self._factions).run()
        return CLOSE_MENU

    def _set_faction(self, pn, r):
        self._factions[pn] = r
        self._players_menu.update_menu(self._build_players_menu())

    def _add_faction_menus(self, menu):
        for pn, (p, pr) in enumerate(zip(self._players, self._factions)):
            for r in ["random_faction"] + self._map.factions:
                if r != pr:
                    menu.append([p,] + style.get(r, "title"),
                                (self._set_faction, pn, r))

    def _build_players_menu(self):
        menu = Menu()
        if len(self._players) < self._map.nb_players_max:
            menu.append(mp.INVITE + mp.QUIET_COMPUTER, (self._add_ai, "easy"))
            menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER,
                        (self._add_ai, "aggressive"))
            menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER + nb2msg(2),
                        (self._add_ai, "ai2"))
        if len(self._players) >= self._map.nb_players_min:
            menu.append(mp.START, self._run_game)
        if len(self._map.factions) > 1:
            self._add_faction_menus(menu)
        menu.append(mp.CANCEL, CLOSE_MENU, mp.CANCEL_THIS_GAME)
        return menu

    def _open_players_menu(self, m):
        # note: won't work with factions defined in the map
        style.load(res.get_text_file("ui/style", append=True, localize=True))
        self._players = [config.login]
        self._factions = ["random_faction"]
        self._map = m
        self._players_menu = self._build_players_menu()
        self._players_menu.loop()

    def run(self):
        menu = Menu(mp.START_A_GAME_ON, remember="mapmenu")
        for m in worlds_multi():
            menu.append(m.title, (self._open_players_menu, m))
        menu.append(mp.QUIT2, None)
        menu.run()


def single_player_menu():
    Menu(
        mp.MAKE_A_SELECTION,
        [(c.title, c) for c in campaigns()] + [
            (mp.START_A_GAME_ON, TrainingMenu().run),
#            (mp.RESTORE, restore_game),
            (mp.BACK, CLOSE_MENU),
        ]).loop()

def server_menu():
    Menu(mp.WHAT_KIND_OF_SERVER, [
        (mp.SIMPLE_SERVER, (start_server_and_connect, "admin_only"),
         mp.SIMPLE_SERVER_EXPLANATION),
        (mp.PUBLIC_SERVER, (start_server_and_connect, ""),
         mp.PUBLIC_SERVER_EXPLANATION),
        (mp.PRIVATE_SERVER,
         (start_server_and_connect, "admin_only no_metaserver"),
         mp.PRIVATE_SERVER_EXPLANATION),
        (mp.CANCEL, None),
        ]).run()

def set_and_launch_mod(mods):
    config.mods = mods
    config.save()
    res.set_mods(config.mods)
    main_menu() # update the menu title
    raise SystemExit

def mods_menu():
    mods_menu = Menu(mp.MODS)
    mods_menu.append([0], (set_and_launch_mod, ""))
    for mod in res.available_mods():
        mods_menu.append([mod], (set_and_launch_mod, mod))
    mods_menu.append(mp.BACK, CLOSE_MENU)
    mods_menu.run()
    return CLOSE_MENU

def set_and_launch_soundpack(soundpacks):
    config.soundpacks = soundpacks
    config.save()
    res.set_soundpacks(config.soundpacks)
    main_menu() # update the menu title
    raise SystemExit

def soundpacks_menu():
    soundpacks_menu = Menu(mp.SOUNDPACKS)
    soundpacks_menu.append(mp.NOTHING, (set_and_launch_soundpack, ""))
    for soundpack in res.available_soundpacks():
        soundpacks_menu.append([soundpack],
                               (set_and_launch_soundpack, soundpack))
    soundpacks_menu.append(mp.BACK, CLOSE_MENU)
    soundpacks_menu.run()
    return CLOSE_MENU

def options_menu():
    Menu(mp.OPTIONS_MENU, [
        (mp.MODIFY_LOGIN, modify_login),
        (mp.MODS, mods_menu),
        (mp.SOUNDPACKS, soundpacks_menu),
        (mp.OPEN_USER_FOLDER, open_user_folder),
        (mp.BACK, CLOSE_MENU),
        ]).loop()

def main_menu():
    Menu(
        ["SoundRTS %s %s %s," % (VERSION, res.mods, res.soundpacks)]
        + mp.MAKE_A_SELECTION,
        [
            [mp.SINGLE_PLAYER, single_player_menu, mp.SINGLE_PLAYER_EXPLANATION],
            [mp.MULTIPLAYER2, multiplayer_menu, mp.MULTIPLAYER2_EXPLANATION],
            [mp.SERVER, server_menu, mp.SERVER_EXPLANATION],
            [mp.OBSERVE_RECORDED_GAME, replay_menu],
            [mp.OPTIONS, options_menu, mp.OPTIONS_EXPLANATION],
            [mp.DOCUMENTATION, launch_manual],
            [mp.QUIT2, CLOSE_MENU, mp.QUIT2_EXPLANATION],
        ]).loop()

def launch_manual():
    if os.path.exists("doc/en"):
        p = "doc"
    else:
        p = join(tempfile.gettempdir(), "soundrts/build/doc")
    try:
        lang = best_language_match(preferred_language, os.listdir(p))
    except OSError:
        voice.alert(mp.BEEP)
    else:
        webbrowser.open(join(p, lang, "help-index.htm"))

def main():
    try:
        init_media()
        revision_checker.start_if_needed()
        if "connect_localhost" in sys.argv:
            connect_and_play()
        else:
            main_menu()
    except SystemExit:
        raise
    except:
        exception("error")
    finally:
        close_media()
