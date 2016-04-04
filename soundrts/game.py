import os.path
import pickle
import threading
import time

import pygame
from pygame.locals import KEYDOWN

from clientmedia import sounds, voice, update_display_caption
import clientgame
from clientgameorder import update_orders_list
import definitions
import config
from constants import METASERVER_URL
from definitions import style, rules, load_ai
from lib.log import warning, exception
from mapfile import Map
from msgs import nb2msg
from paths import REPLAYS_PATH, SAVE_PATH, STATS_PATH
import random
import res
import stats
from version import VERSION, compatibility_version
from world import World
from worldclient import DirectClient, Coordinator, ReplayClient, DummyClient, HalfDummyClient, send_platform_version_to_metaserver 


def reload_all():
    update_display_caption()
    res.update_mods_list()
    sounds.load_default()
    rules.load(res.get_text("rules", append=True))
    load_ai(res.get_text("ai", append=True)) # just in case
    style.load(res.get_text("ui/style", append=True, locale=True))
    while(res.alerts):
        voice.alert(res.alerts.pop(0))


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
        self.replay_write(config.mods)
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
        s = stats.Stats(STATS_PATH, METASERVER_URL)
        s.add(self._game_type(), int(world.time / 1000))

    def run(self, speed=config.speed):
        if self.record_replay:
            self.create_replay()
        self.world = World(self.default_triggers, self.seed)
        if self.world.load_and_build_map(self.map):
            style.load(res.get_text("ui/style", append=True, locale=True),
                       self.map.campaign_style,
                       self.map.additional_style)
            sounds.enter_map(self.map.mapfile)
            update_orders_list() # when style has changed
            self.pre_run()
            self.interface = clientgame.GameInterface(self.me, speed=speed)
            self.interface.load_bindings(
                res.get_text("ui/bindings", append=True, locale=True) + "\n" +
                self.map.get_campaign("ui/bindings.txt") + "\n" +
                self.map.get_additional("ui/bindings.txt"))
            self.world.populate_map(self.players, self.alliances, self.factions)
            self.nb_human_players = self.world.current_nb_human_players()
            t = threading.Thread(target=self.world.loop)
            t.daemon = True
            t.start()
            self.interface.loop()
            self._record_stats(self.world)
            self.post_run()
            sounds.exit_map()
            self.world.clean()
        else:
            voice.alert([1029]) # hostile sound
            voice.alert([self.world.map_error])
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

    def __init__(self, map, players, my_login, main_server, seed, speed):
        self.map = map
        computers, humans = self._computers_and_humans(players, my_login)
        self.me = Coordinator(my_login, main_server, humans, self)
        humans[humans.index(None)] = self.me
        self.players = humans + computers # humans first because the first in the list is the game admin
        self.seed = seed
        self.speed = speed
        self.main_server = main_server
        if len(humans) > 1:
            self.allow_cheatmode = False

    def run(self):
        _MultiplayerGame.run(self, speed=self.speed)

    def _countdown(self):
        voice.important([4062]) # "the game starts in 5 seconds"
        for n in [5, 4, 3, 2, 1, 0]:
            voice.item(nb2msg(n))
            time.sleep(1)
        pygame.event.clear(KEYDOWN)

    def pre_run(self):
        nb_human_players = len([p for p in self.players if p.login != "ai"])
        if nb_human_players > 1:
            send_platform_version_to_metaserver(self.map.get_name(), nb_human_players)
            self._countdown()

    def post_run(self):
        # alert the server of the exit from the game interface
        if self.interface.forced_quit:
            self.main_server.write_line("abort_game")
        else:
            self.main_server.write_line("quit_game")
        self.say_score() # say score only after quit_game to avoid blocking the main server
        voice.menu([4010, 4030]) # "menu" "please make a selection" (long enough to allow history navigation)

    def _computers_and_humans(self, players, my_login):
        computers = []
        humans = []
        for p in players:
            if p in ["ai_aggressive", "ai_easy"]:
                computers.append(DummyClient(p[3:]))
            else:
                if p != my_login:
                    humans.append(HalfDummyClient(p))
                else:
                    humans.append(None) # marked for further replacement, because the order must be the same (the worlds must be the same)
        return computers, humans


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
            voice.info([105])
        except:
            exception("save game failed")
            voice.alert([1029]) # hostile sound
        self.world.restore_links_for_savegame()

    def run_on(self):
        if self.record_replay:
            self._replay_file = open(os.path.join(REPLAYS_PATH, "%s.txt" % int(time.time())), "w")
            self._replay_file.write(self._replay_file_content)
        sounds.enter_map(self.map.mapfile)
        self.world.restore_links_for_savegame()
        rules.copy(self._rules)
        definitions._ai = self._ai
        style.copy(self._style)
        update_orders_list() # when style has changed
        self.interface.set_self_as_listener()
        t = threading.Thread(target=self.world.loop)
        t.daemon = True
        t.start()
        # Because the simulation is in a different thread,
        # sometimes the interface "forgets" to ask for an
        # update. Maybe a better communication protocol
        # between interface and simulation would solve
        # this problem ("update" and "no_end_of_update_yet"
        # should contain the simulation time, maybe). Maybe
        # some data in a queue has been lost.
        self.interface.asked_to_update = False
        self.interface.loop()
        self._record_stats(self.world)
        self.post_run()
        self.world.clean()


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
            sounds.play_sequence(self.world.intro)

    def post_run(self):
        _Game.post_run(self)
        self._has_victory = self.me.has_victory()

    def has_victory(self):
        return self._has_victory

    def run_on(self):
        sounds.enter_campaign(self.map.campaign.path)
        _Savable.run_on(self)
        self.map.run_next_step(self)
        sounds.exit_campaign()


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
        if mods != config.mods:
            config.mods = mods
            reload_all()
        _compatibility_version = self.replay_read()
        if _compatibility_version != compatibility_version():
            voice.alert([1029, 4012]) # hostile sound  "version error"
            warning("Version mismatch. Version should be: %s. Mods should be: %s.",
                    version, mods)
        campaign_path_or_packed_map = self.replay_read()
        if game_type_name == "mission" and "***" not in campaign_path_or_packed_map:
            from soundrts.campaign import Campaign
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
            if x in ["aggressive", "easy"]: # the "ai_" prefix wasn't recorded
                self.players += [DummyClient(x)]
            else:
                self.players += [HalfDummyClient(x)]
                self.me.nb_humans += 1

    def replay_read(self):
        s = self._file.readline()
        if s and s.endswith("\n"):
            s = s[:-1]
        return s

    def pre_run(self):
        voice.info([4316])
        voice.flush()

    def run(self):
        if getattr(self.map, "campaign", None):
            self.map.campaign.load_resources()
        try:
            _Game.run(self)
        finally:
            if getattr(self.map, "campaign", None):
                self.map.campaign.unload_resources()
