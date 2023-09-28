from . import config

config.load()

# hide the pygame support prompt from players
if not config.debug_mode:
    import os

    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from .lib import log, resource
from .lib.log import exception, warning
from .paths import CLIENT_LOG_PATH
from .version import VERSION_FOR_BUG_REPORTS

log.set_version(VERSION_FOR_BUG_REPORTS)
log.clear_handlers()
log.add_secure_file_handler(CLIENT_LOG_PATH, "w")
log.add_http_handler("http://jlpo.free.fr/soundrts/metaserver")
log.add_console_handler()

import locale

try:
    locale.setlocale(locale.LC_ALL, "")
except:
    warning("couldn't set locale")

import os
import sys
import time
import webbrowser

import cloudpickle

from . import discovery
from . import msgparts as mp
from . import stats
from .clientmedia import close_media, init_media, voice, app_title
from .clientmenu import CLOSE_MENU, Menu, input_string
from .clientserver import (
    connect_and_play,
    server_delay,
    start_server_and_connect,
)
from .clientversion import revision_checker
from .definitions import style, rules
from .game import ReplayGame, TrainingGame
from .lib.msgs import nb2msg
from .lib.resource import best_language_match, preferred_language, res
from .metaserver import servers_list
from .paths import CONFIG_DIR_PATH, REPLAYS_PATH, SAVE_PATH
from .version import server_is_compatible


def choose_server_ip_in_a_list():
    servers = servers_list(voice)
    try:
        local = discovery.local_server()
        if local:
            version, port, login = local[1].split(" ", 2)
            servers.insert(
                0, " ".join(("0", local[0], version, local[0] + "_" + login, port))
            )
    except:
        warning("error while searching for a local server")
    total = 0
    compatible = 0
    menu = Menu()
    for s in servers:
        if s == "":
            continue
        try:
            _, ip, version, login, port = s.split()
        except ValueError:
            warning("line not recognized from the metaserver: %s", s)
        else:
            total += 1
            if server_is_compatible(version):
                compatible += 1
                delay = server_delay(ip, port)
                if delay is not None:
                    menu.append(
                        [login],
                        (connect_and_play, ip, port),
                        [f"{int(delay * 1000)}ms", ","] + mp.SERVER_HOSTED_BY + [login],
                    )
    menu.choices.sort(key=lambda x: int(x[2][0][:-2]))
    menu.title = nb2msg(compatible) + mp.SERVERS_ON + nb2msg(total)
    menu.append(mp.CANCEL2, None, mp.GO_BACK_TO_PREVIOUS_MENU)
    menu.run()


def enter_server_ip():
    host = input_string([], r"^[A-Za-z0-9\.]$")
    if host == "":
        host = "localhost"
    if host:
        connect_and_play(host)


def multiplayer_menu():
    if config.login == "player":
        voice.alert(mp.ENTER_NEW_LOGIN)
        modify_login()
    menu = Menu(
        mp.MAKE_A_SELECTION,
        [
            (mp.CHOOSE_SERVER_IN_LIST, choose_server_ip_in_a_list),
            (mp.ENTER_SERVER_IP, enter_server_ip),
            (mp.CANCEL, None),
        ],
    )
    menu.run()


def replay(n):
    ReplayGame(os.path.join(REPLAYS_PATH, n)).run()


def replay_filenames(minimal_size=None):
    for n in sorted(os.listdir(REPLAYS_PATH), reverse=True):
        if not minimal_size or len(open(os.path.join(REPLAYS_PATH, n)).read()) >= minimal_size:
            yield n


def replay_menu():
    menu = Menu(mp.OBSERVE_RECORDED_GAME)
    for n in replay_filenames():
        if n.endswith(".txt"):
            try:
                menu.append([time.strftime("%c", time.localtime(int(n[:-4])))], (replay, n))
            except ValueError:
                menu.append((n[:-4]), (replay, n))
    menu.append(mp.QUIT2, None)
    menu.run()


def modify_login():
    login = input_string(
        mp.ENTER_NEW_LOGIN + mp.USE_LETTERS_AND_NUMBERS_ONLY, "^[a-zA-Z0-9]$"
    )
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
    f = open(n, "rb")
    try:
        i = int(stats.Stats(None, None)._get_weak_user_id())
        j = int(f.readline())
    except:
        i = 0
        j = "error"
    if i == j:
        try:
            game_session = cloudpickle.load(f)
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


class TrainingMenu:
    def _add_ai(self, ai_type):
        self._players.append(ai_type)
        self._factions.append("random_faction")
        self._players_menu.update_menu(self._build_players_menu())

    def _run_game(self):
        alliances = ["1"] + ["2"] * (len(self._players) - 1)
        TrainingGame(self._map, self._players, self._factions, alliances).run()
        return CLOSE_MENU

    def _set_faction(self, pn, r):
        self._factions[pn] = r
        self._players_menu.update_menu(self._build_players_menu())

    def _add_faction_menus(self, menu):
        for pn, (p, pr) in enumerate(zip(self._players, self._factions)):
            for r in ["random_faction"] + rules.factions:
                if r != pr:
                    menu.append(
                        [p,] + style.get(r, "title"), (self._set_faction, pn, r)
                    )

    def _build_players_menu(self):
        menu = Menu()
        if len(self._players) < self._map.nb_players_max:
            self._add_ai_invite_menu(menu)
        if len(self._players) >= self._map.nb_players_min:
            menu.append(mp.START, self._run_game)
        if len(rules.factions) > 1:
            self._add_faction_menus(menu)
        menu.append(mp.CANCEL, CLOSE_MENU, mp.CANCEL_THIS_GAME)
        return menu

    def _add_ai_invite_menu(self, menu):
        menu.append(mp.INVITE + mp.QUIET_COMPUTER, (self._add_ai, "easy"))
        menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER, (self._add_ai, "aggressive"))
        menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER + nb2msg(2), (self._add_ai, "ai2"))

    def _open_players_menu(self, m):
        self._players = [config.login]
        self._factions = ["random_faction"]
        self._map = m
        res.set_map(m)
        try:
            self._players_menu = self._build_players_menu()
            self._players_menu.loop()
        finally:
            res.set_map()

    def run(self):
        menu = Menu(mp.START_A_GAME_ON, remember="mapmenu")
        for m in res.multiplayer_maps():
            menu.append(m.title, (self._open_players_menu, m))
        menu.append(mp.QUIT2, None)
        menu.run()


def single_player_menu():
    Menu(
        mp.MAKE_A_SELECTION,
        [(c.title, c) for c in res.campaigns()]
        + [
            (mp.START_A_GAME_ON, TrainingMenu().run),
            (mp.RESTORE, restore_game),
            (mp.BACK, CLOSE_MENU),
        ],
    ).loop()


def server_menu():
    Menu(
        mp.WHAT_KIND_OF_SERVER,
        [
            (
                mp.SIMPLE_SERVER,
                (start_server_and_connect, "admin_only"),
                mp.SIMPLE_SERVER_EXPLANATION,
            ),
            (
                mp.PUBLIC_SERVER,
                (start_server_and_connect, ""),
                mp.PUBLIC_SERVER_EXPLANATION,
            ),
            (
                mp.PRIVATE_SERVER,
                (start_server_and_connect, "admin_only no_metaserver"),
                mp.PRIVATE_SERVER_EXPLANATION,
            ),
            (mp.CANCEL, None),
        ],
    ).run()


def set_and_launch_mod(mods):
    config.mods = mods
    config.save()
    res.set_mods(config.mods)
    main_menu()  # update the menu title
    raise SystemExit


def mods_menu():
    res.update_packages()
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
    main_menu()  # update the menu title
    raise SystemExit


def soundpacks_menu():
    res.update_packages()
    soundpacks_menu = Menu(mp.SOUNDPACKS)
    soundpacks_menu.append(mp.NOTHING, (set_and_launch_soundpack, ""))
    for soundpack in res.available_soundpacks():
        soundpacks_menu.append([soundpack], (set_and_launch_soundpack, soundpack))
    soundpacks_menu.append(mp.BACK, CLOSE_MENU)
    soundpacks_menu.run()
    return CLOSE_MENU


def options_menu():
    Menu(
        mp.OPTIONS_MENU,
        [
            (mp.MODIFY_LOGIN, modify_login),
            (mp.MODS, mods_menu),
            (mp.SOUNDPACKS, soundpacks_menu),
            (mp.OPEN_USER_FOLDER, open_user_folder),
            (mp.BACK, CLOSE_MENU),
        ],
    ).loop()


def main_menu():
    Menu(
        [app_title() + ","] + mp.MAKE_A_SELECTION,
        [
            [mp.SINGLE_PLAYER, single_player_menu, mp.SINGLE_PLAYER_EXPLANATION],
            [mp.MULTIPLAYER2, multiplayer_menu, mp.MULTIPLAYER2_EXPLANATION],
            [mp.SERVER, server_menu, mp.SERVER_EXPLANATION],
            [mp.OBSERVE_RECORDED_GAME, replay_menu],
            [mp.OPTIONS, options_menu, mp.OPTIONS_EXPLANATION],
            [mp.DOCUMENTATION, launch_manual],
            [mp.QUIT2, CLOSE_MENU, mp.QUIT2_EXPLANATION],
        ],
    ).loop()


def launch_manual():
    p = "doc"
    try:
        lang = best_language_match(preferred_language, os.listdir(p))
    except OSError:
        voice.alert(mp.BEEP)
    else:
        webbrowser.open(os.path.join(p, lang, "help-index.htm"))


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
