import os.path
import pickle
import threading
import time

import pygame
from pygame.locals import KEYDOWN

from clientmedia import voice, play_sequence
import clientgame
from clientgameorder import update_orders_list
import definitions
import config
from definitions import style, rules
from lib.log import warning, exception
from lib.msgs import nb2msg
from mapfile import Map
import msgparts as mp
from paths import CUSTOM_BINDINGS_PATH, REPLAYS_PATH, SAVE_PATH
import random
import res
import stats
from version import VERSION, compatibility_version
from world import World
from worldclient import DirectClient, Coordinator, ReplayClient, DummyClient, RemoteClient, send_platform_version_to_metaserver 


PROFILE = False


class _Game(object):

    default_triggers = () # empty tuple; a tuple is immutable
    game_type_name = None
    alliances = ()
    factions = ()
    record_replay = True
    allow_cheatmode = True

    def create_replay(self):
        self._replay_file = open(os.path.join(REPLAYS_PATH, "%s.txt" % int(time.time())), "w")
        self.replay_write(self.game_type_name)
        players = " ".join([p.login for p in self.players])
        self.replay_write(self.map.get_name() + " " + players)
        self.replay_write(VERSION)
        self.replay_write(res.mods)
        self.replay_write(compatibility_version())
        if self.game_type_name == "mission":
            self.replay_write(self.map.campaign.path)
            self.replay_write(str(self.map.id))
        else:
            self.replay_write(self.map.pack())
        self.replay_write(players)
        self.replay_write(" ".join(map(str, self.alliances)))
        self.replay_write(" ".join(self.factions))
        self.replay_write(str(self.seed))

    def replay_write(self, s):
        self._replay_file.write(s + "\n")
      
    def _game_type(self):
        return "%s/%s/%s" % (VERSION,
                             self.game_type_name + "-" + self.map.get_name(),
                             self.nb_human_players)

    def _record_stats(self, world):
        stats.add(self._game_type(), int(world.time / 1000))

    def run(self, speed=config.speed):
        if self.record_replay:
            self.create_replay()
        self.world = World(self.default_triggers, self.seed)
        if self.world.load_and_build_map(self.map):
            self.map.load_style(res)
            try:
                self.map.load_resources()
                update_orders_list() # when style has changed
                self.pre_run()
                if self.world.objective:
                    voice.confirmation(mp.OBJECTIVE + self.world.objective)
                self.interface = clientgame.GameInterface(self.me, speed=speed)
                b = res.get_text_file("ui/bindings", append=True, localize=True)
                b += "\n" + self.map.get_campaign("ui/bindings.txt")
                b += "\n" + self.map.get_additional("ui/bindings.txt")
                try:
                    b += "\n" + open(CUSTOM_BINDINGS_PATH, "U").read()
                except IOError:
                    pass
                self.interface.load_bindings(b)
                self.world.populate_map(self.players)
                self.nb_human_players = self.world.current_nb_human_players()
                t = threading.Thread(target=self.world.loop)
                t.daemon = True
                t.start()
                if PROFILE:
                    import cProfile
                    cProfile.runctx("self.interface.loop()", globals(), locals(), "interface_profile.tmp")
                else:
                    self.interface.loop()
                self._record_stats(self.world)
                self.post_run()
            finally:
                self.map.unload_resources()
            self.world.stop()
        else:
            voice.alert(mp.BEEP + [self.world.map_error])
        if self.record_replay:
            self._replay_file.close()

    def pre_run(self):
        pass

    def post_run(self):
        self.say_score()

    def say_score(self):
        for msg in self.me.player.score_msgs:
            voice.info(msg)
        voice.flush()


class _MultiplayerGame(_Game):

    default_triggers = (
        ["players", ["no_enemy_player_left"], ["victory"]],
        ["players", ["no_building_left"], ["defeat"]],
        ["computers", ["no_unit_left"], ["defeat"]],
        ) # a tuple is immutable


class MultiplayerGame(_MultiplayerGame):

    game_type_name = "multiplayer"

    def _clients(self, players, local_login, main_server):
        clients = []
        for login, a, f in players:
            if login.startswith("ai_"):
                c = DummyClient(login[3:])
            else:
                if login != local_login:
                    c = RemoteClient(login)
                else:
                    c = Coordinator(local_login, main_server, self)
                    self.me = c
            c.alliance = a
            c.faction = f
            clients.append(c)
        return clients

    @property
    def humans(self):
        return [c for c in self.players if c.__class__ != DummyClient]

    def __init__(self, map, players, local_login, main_server, seed, speed):
        self.map = map
        self.players = self._clients(players, local_login, main_server)
        self.seed = seed
        self.speed = speed
        self.main_server = main_server
        if len(self.humans) > 1:
            self.allow_cheatmode = False

    def run(self):
        _MultiplayerGame.run(self, speed=self.speed)

    def _countdown(self):
        voice.important(mp.THE_GAME_WILL_START)
        for n in [5, 4, 3, 2, 1, 0]:
            voice.item(nb2msg(n))
            time.sleep(1)
        pygame.event.clear(KEYDOWN)

    def pre_run(self):
        if len(self.humans) > 1:
            send_platform_version_to_metaserver(self.map.get_name(), len(self.humans))
            self._countdown()

    def post_run(self):
        self.main_server.write_line("quit_game")
        # say score only after quit_game to avoid blocking the main server
        self.say_score()
        voice.menu(mp.MENU + mp.MAKE_A_SELECTION)
        # (long enough to allow history navigation)


class _Savable(object):

    def __getstate__(self):
        odict = self.__dict__.copy()
        odict.pop('_replay_file', None)
        return odict

    def save(self):
        f = open(SAVE_PATH, "w")
        i = stats.Stats(None, None)._get_weak_user_id()
        f.write("%s\n" % i)
        self.world.remove_links_for_savegame()
        self._rules = rules
        self._ai = definitions._ai
        self._style = style
        if self.record_replay:
            self._replay_file.flush()
            os.fsync(self._replay_file.fileno()) # just to be sure
            self._replay_file_content = open(self._replay_file.name).read()
        try:
            pickle.dump(self, f)
            voice.info(mp.OK)
        except:
            exception("save game failed")
            voice.alert(mp.BEEP)
        self.world.restore_links_for_savegame()

    def run_on(self):
        if self.record_replay:
            self._replay_file = open(os.path.join(REPLAYS_PATH, "%s.txt" % int(time.time())), "w")
            self._replay_file.write(self._replay_file_content)
        try:
            self.map.load_resources()
            self.world.restore_links_for_savegame()
            rules.copy(self._rules)
            definitions._ai = self._ai
            style.copy(self._style)
            update_orders_list() # when style has changed
            self.interface.set_self_as_listener()
            t = threading.Thread(target=self.world.loop)
            t.daemon = True
            t.start()
            self.interface.loop()
            self._record_stats(self.world)
            self.post_run()
            self.world.stop()
        finally:
            self.map.unload_resources()


class TrainingGame(_MultiplayerGame, _Savable):

    game_type_name = "training"

    def __init__(self, map, players):
        self.map = map
        self.seed = random.randint(0, 10000)
        self.me = DirectClient(config.login, self)
        self.players = [self.me] + [DummyClient(x) for x in players[1:]]


class MissionGame(_Game, _Savable):

    game_type_name = "mission"
    _has_victory = False

    def __init__(self, map):
        self.map = map
        self.seed = random.randint(0, 10000)
        self.me = DirectClient(config.login, self)
        self.players = [self.me]

    def pre_run(self):
        if self.world.intro:
            play_sequence(self.world.intro)

    def post_run(self):
        _Game.post_run(self)
        self._has_victory = self.me.has_victory()

    def has_victory(self):
        return self._has_victory

    def run_on(self):
        try:
            self.map.campaign.load_resources()
            _Savable.run_on(self)
            self.map.run_next_step(self)
        finally:
            self.map.campaign.unload_resources()


class ReplayGame(_Game):

    game_type_name = "replay" # probably useless (or maybe for stats)
    record_replay = False

    def __init__(self, replay):
        self._file = open(replay)
        game_type_name = self.replay_read()
        if game_type_name in ("multiplayer", "training"):
            self.default_triggers = _MultiplayerGame.default_triggers
        game_name = self.replay_read()
        voice.alert([game_name])
        version = self.replay_read()
        mods = self.replay_read()
        res.set_mods(mods)
        _compatibility_version = self.replay_read()
        if _compatibility_version != compatibility_version():
            voice.alert(mp.BEEP + mp.VERSION_ERROR)
            warning("Version mismatch. Version should be: %s. Mods should be: %s.",
                    version, mods)
        campaign_path_or_packed_map = self.replay_read()
        if game_type_name == "mission" and "***" not in campaign_path_or_packed_map:
            from campaign import Campaign
            self.map = Campaign(campaign_path_or_packed_map)._get(int(self.replay_read()))
        else:
            self.map = Map()
            self.map.unpack(campaign_path_or_packed_map)
        players = self.replay_read().split()
        self.alliances = map(int, self.replay_read().split())
        self.factions = self.replay_read().split()
        self.seed = int(self.replay_read())
        self.me = ReplayClient(players[0], self)
        self.players = [self.me]
        for x in players[1:]:
            if x.startswith("ai_"):
                x = x[3:]
            if x in ["aggressive", "easy", "ai2"]:
                self.players += [DummyClient(x)]
            else:
                self.players += [RemoteClient(x)]
                self.me.nb_humans += 1

    def replay_read(self):
        s = self._file.readline()
        if s and s.endswith("\n"):
            s = s[:-1]
        return s

    def pre_run(self):
        voice.info(mp.OBSERVE_ANOTHER_PLAYER_EXPLANATION)
        voice.flush()

    def run(self):
        if getattr(self.map, "campaign", None):
            self.map.campaign.load_resources()
        try:
            _Game.run(self)
        finally:
            if getattr(self.map, "campaign", None):
                self.map.campaign.unload_resources()
