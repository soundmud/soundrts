import pickle
import sys
import threading
import time

from clientmedia import *
import clientgame
import clientmenu
import clientstyle
import clientworld
import config
from constants import *
from mapfile import *
from paths import *
import res
import tts
from world import *
from worldclient import *


class _Game(object):

    default_triggers = () # empty tuple; a tuple is immutable
    seed = None
    game_type_name = None
    alliances = ()
    races = ()

    def _game_type(self):
        return "%s/%s/%s" % (VERSION,
                             self.game_type_name + "-" + self.map.get_name(),
                             self.nb_human_players)

    def _record_stats(self, world):
        s = stats.Stats(STATS_PATH, METASERVER_URL)
        s.add(self._game_type(), int(world.time / 1000))

    def run(self, speed=config.speed):
        self.world = World(self.default_triggers, self.seed)
        if self.world.load_and_build_map(self.map):
            load_style(res.get_text("ui/style", append=True, locale=True),
                       self.map.campaign_style,
                       self.map.additional_style)
            sounds.enter_map(self.map.mapfile)
            clientworld.update_orders_list() # when style has changed
            self.pre_run()
            self.interface = clientgame.GameInterface(self.me, speed=speed)
            self.interface.load_bindings(
                res.get_text("ui/bindings", append=True, locale=True) + "\n" +
                self.map.get_campaign("ui/bindings.txt") + "\n" +
                self.map.get_additional("ui/bindings.txt"))
            self.world.populate_map(self.players, self.alliances, self.races)
            self.nb_human_players = self.world.current_nb_human_players()
            threading.Thread(target=self.world.loop).start()
            self.interface.loop()
            self._record_stats(self.world)
            self.post_run()
            sounds.exit_map()
            self.world.clean()
        else:
            voice.alert([1029]) # hostile sound
            if tts.is_available:
                voice.alert([self.world.map_error])

    def pre_run(self):
        pass

    def post_run(self):
        self.say_score()

    def say_score(self):
        for msg in self.interface.get_score_msgs():
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
        self.me = Coordinator(my_login, main_server, humans)
        humans[humans.index(None)] = self.me
        self.players = humans + computers # humans first because the first in the list is the game admin
        self.seed = seed
        self.speed = speed
        self.main_server = main_server

    def run(self):
        _MultiplayerGame.run(self, speed=self.speed)

    def _countdown(self):
        voice.important([4062]) # "the game starts in 5 seconds"
        for n in [5, 4, 3, 2, 1, 0]:
            voice.item(nombre(n))
            time.sleep(1)
        pygame.event.clear(KEYDOWN)

    def pre_run(self):
        nb_human_players = len([p for p in self.players if p.login != "ai"])
        if nb_human_players > 1:
            if compatibility_version() != COMPATIBILITY_VERSION:
                warning("rules.txt or ai.txt has been modified"
                        " after the program started: exit...")
                sys.exit()
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

    def save(self):
        f = open(SAVE_PATH, "w")
        i = stats.Stats(None, None)._get_weak_user_id()
        f.write("%s\n" % i)
        self.world.remove_links_for_savegame()
        self._rules = clientstyle._rules
        self._ai = clientstyle._ai
        self._style = clientstyle._style
        try:
            pickle.dump(self, f)
            voice.info([105])
        except:
            exception("save game failed")
            voice.alert([1029]) # hostile sound
        self.world.restore_links_for_savegame()

    def run_on(self):
        sounds.enter_map(self.map.mapfile)
        self.world.restore_links_for_savegame()
        clientstyle._rules = self._rules
        clientstyle._ai = self._ai
        clientstyle._style = self._style
        clientworld.update_orders_list() # when style has changed
        self.interface.set_self_as_listener()
        threading.Thread(target=self.world.loop).start()
        self.interface.loop()
        self._record_stats(self.world)
        self.post_run()
        self.world.clean()


class TrainingGame(_MultiplayerGame, _Savable):

    game_type_name = "training"

    def __init__(self, map, computers):
        self.map = map
        self.me = DirectClient(config.login, self)
        self.players = [self.me] + [DummyClient(x) for x in computers]


class MissionGame(_Game, _Savable):

    game_type_name = "mission"
    _has_victory = False

    def __init__(self, map):
        self.map = map
        self.me = DirectClient(config.login, self)
        self.players = [self.me]

    def pre_run(self):
        if self.world.intro: # only in missions (streaming sound)
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
