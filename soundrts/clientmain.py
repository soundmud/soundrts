from lib import log
from version import VERSION_FOR_BUG_REPORTS
from paths import CLIENT_LOG_PATH
log.set_version(VERSION_FOR_BUG_REPORTS)
log.add_secure_file_handler(CLIENT_LOG_PATH, "w")
log.add_http_handler("http://jlpo.free.fr/soundrts/metaserver")
log.add_console_handler()

import locale
try:
    locale.setlocale(locale.LC_ALL, '')
except:
    from lib.log import warning
    warning("couldn't set locale")

import os
import pickle
import sys
import time
import urllib
import webbrowser

from clientmedia import voice, init_media, close_media
from clientmenu import Menu, input_string, END_LOOP
from clientserver import connect_and_play, start_server_and_connect
from clientversion import revision_checker
import config
from constants import MAIN_METASERVER_URL
from definitions import style
from game import TrainingGame, ReplayGame
from lib.log import exception
from lib.msgs import nb2msg
from paths import CONFIG_DIR_PATH, REPLAYS_PATH, SAVE_PATH
import res
import stats
from version import compatibility_version


_ds = open("cfg/default_servers.txt").readlines()
_ds = [_x.split() for _x in _ds]
DEFAULT_SERVERS = [" ".join(["0"] + _x[:1] + [compatibility_version()] + _x[1:]) for _x in _ds]
SERVERS_LIST_HEADER = "SERVERS_LIST"
SERVERS_LIST_URL = MAIN_METASERVER_URL + "servers.php?header=%s&include_ports=1" % SERVERS_LIST_HEADER


class Application(object):

    def choose_server_ip_in_a_list(self):
        servers_list = None
        try:
            f = urllib.urlopen(SERVERS_LIST_URL)
            if f.read(len(SERVERS_LIST_HEADER)) == SERVERS_LIST_HEADER:
                servers_list = f.readlines()
        except:
            pass
        if servers_list is None:
            voice.alert([1029]) # hostile sound
            warning("couldn't get the servers list from the metaserver"
                    " => using the default servers list")
            servers_list = DEFAULT_SERVERS
        nb = 0
        menu = Menu()
        for s in servers_list:
            try:
                ip, version, login, port = s.split()[1:]
                # ignore the first parameter (time)
            except:
                warning("line not recognized from the metaserver: %s", s)
                continue
            nb += 1
            if version == compatibility_version():
                menu.append([login, 4073, login], (connect_and_play, ip, port))
        menu.title = nb2msg(len(menu.choices)) + [4078] + nb2msg(nb) + [4079]
        menu.append([4075, 4076], None)
        menu.run()

    def enter_server_ip(self):
        host = input_string([], "^[A-Za-z0-9\.]$")
        if host:
            connect_and_play(host)

    def multiplayer_menu(self):
        revision_checker.start_if_needed()
        if config.login == "player":
            voice.alert([4235]) # type your new login
            self.modify_login()
        menu = Menu([4030], [
            ([4119], self.choose_server_ip_in_a_list),
            ([4120], self.enter_server_ip),
            ([4048], None),
             ])
        menu.run()

    def restore_game(self):
        n = SAVE_PATH
        if not os.path.exists(n):
            voice.alert([1029]) # hostile sound
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
                voice.alert([1029]) # hostile sound
                return
            game_session.run_on()
        else:
            warning("savegame file is not from this machine")
            voice.alert([1029]) # hostile sound

    def training_menu_invite(self, ai_type):
        self.players.append(ai_type)
        self.factions.append("random_faction")
        self.menu.update_menu(self.build_training_menu_after_map())

    def training_menu_after_map(self, m):
        style.load(res.get_text_file("ui/style", append=True, localize=True)) # XXX: won't work with factions defined in the map
        self.players = [config.login]
        self.factions = ["random_faction"]
        self.map = m
        self.menu = self.build_training_menu_after_map()
        self.menu.loop()

    def start_training_game(self):
        game = TrainingGame(self.map, self.players)
        game.factions = self.factions
        game.run()
        return END_LOOP

    def set_faction(self, pn, r):
        self.factions[pn] = r
        self.menu.update_menu(self.build_training_menu_after_map())

    def _add_faction_menu(self, menu, pn, p, pr):
        if len(self.map.factions) > 1:
            for r in ["random_faction"] + self.map.factions:
                if r != pr:
                    menu.append([p,] + style.get(r, "title"),
                                (self.set_faction, pn, r))

    def build_training_menu_after_map(self):
        menu = Menu()
        if len(self.players) < self.map.nb_players_max:
            menu.append([4058, 4258], (self.training_menu_invite, "easy"))
            menu.append([4058, 4257], (self.training_menu_invite,
                                       "aggressive"))
        if len(self.players) >= self.map.nb_players_min:
            menu.append([4059], self.start_training_game)
        for pn, (p, pr) in enumerate(zip(self.players, self.factions)):
            self._add_faction_menu(menu, pn, p, pr)
        menu.append([4048, 4060], END_LOOP)
        return menu

    def training_menu(self):
        menu = Menu([4055], remember="mapmenu")
        for m in res.worlds_multi():
            menu.append(m.title, (self.training_menu_after_map, m))
        menu.append([4041], None)
        menu.run()

    def replay(self, n):
        ReplayGame(os.path.join(REPLAYS_PATH, n)).run()

    def replay_menu(self):
        menu = Menu([4315])
        for n in sorted(os.listdir(REPLAYS_PATH), reverse=True):
            if n.endswith(".txt"):
                menu.append([time.strftime("%c", time.localtime(int(n[:-4])))], (self.replay, n))
        menu.append([4041], None)
        menu.run()

    def modify_login(self):
        login = input_string([4235, 4236], "^[a-zA-Z0-9]$") # type your new
                                        # login ; use alphanumeric characters
        if login == None:
            voice.alert([4238]) # current login kept
        elif (len(login) < 1) or (len(login) > 20):
            voice.alert([4237, 4238]) # incorrect login ; current login kept
        else:
            voice.alert([4239, login]) # new login:
            config.login = login
            config.save()

    def main(self):
        def open_user_folder():
            webbrowser.open(CONFIG_DIR_PATH)
        single_player_menu = Menu([4030],
            [(c.title, c) for c in res.campaigns()] +
            [
            ([4055], self.training_menu),
            ([4113], self.restore_game),
            ([4118], END_LOOP),
            ])
        server_menu = Menu([4043], [
            ([4044, 4045], (start_server_and_connect, "admin_only")),
            ([4046, 4047], (start_server_and_connect, "")),
            ([4121, 4122], (start_server_and_connect,
                            "admin_only no_metaserver")),
            ([4048], None),
            ])
        def set_and_launch_mod(mods):
            config.mods = mods
            config.save()
            res.set_mods(config.mods)
            main_menu().loop() # update the menu title
            raise SystemExit
        def mods_menu():
            mods_menu = Menu(["Mods"])
            mods_menu.append([4340], (set_and_launch_mod, ""))
            mods_menu.append(["soundpack"], (set_and_launch_mod, "soundpack"))
            for mod in res.available_mods():
                if mod != "soundpack":
                    for mods in ((mod, ), (mod, "soundpack")):
                        mods_menu.append([" + ".join(mods)], (set_and_launch_mod, ",".join(reversed(mods))))
            mods_menu.append([4118], END_LOOP)
            mods_menu.run()
            return END_LOOP
        options_menu = Menu([4086], [
            ([4087], self.modify_login),
            (("Mods", ), mods_menu),
            ([4336], open_user_folder),
            ([4118], END_LOOP),
            ])
        def main_menu():
            import version
            return Menu(["SoundRTS %s %s," % (version.VERSION, res.mods), 4030], [
            [[4031, 4032], single_player_menu.loop],
            [[4033, 4034], self.multiplayer_menu],
            [[4035, 4036], server_menu],
            [[4315], self.replay_menu],
            [[4037, 4038], options_menu.loop],
            [[4337], launch_manual],
            [[4041, 4042], END_LOOP],
            ])
        def launch_manual():
            webbrowser.open(os.path.realpath("doc/help-index.htm"))
        if "connect_localhost" in sys.argv:
            connect_and_play()
        else:
            main_menu().loop()


def main():
    try:
        try:
            init_media()
            revision_checker.start_if_needed()
            Application().main()
        except SystemExit:
            raise
        except:
            exception("error")
    finally:
        close_media()


if __name__ == "__main__":
    main()
