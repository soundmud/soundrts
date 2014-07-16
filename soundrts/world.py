import math
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import os.path
import Queue
import re
import string
import time

import collision
from commun import *
import config
from constants import *
import g
from paths import MAPERROR_PATH
import res
from servermsg import * # XXXXXXX
import stats
import worldclient
from worldexit import *
from worldplayer import *
import worldrandom
from worldroom import *
from worldunit import *


GLOBAL_FOOD_LIMIT = 80


class Type(object):

    def init_dict(self, target):
        target.type_name = self.type_name
        for k, v in self.dct.items():
            if k == "class":
                continue
            if (hasattr(self.cls, k) or
                k.endswith("_bonus") and hasattr(self.cls, k[:-6])
                ) and not callable(getattr(self.cls, k, None)):
                if k == "cost":
                    normalize_cost_or_resources(v)
                setattr(target, k, v)
            elif target is self:
                warning("in %s: %s doesn't have any attribute called '%s'", self.type_name, self.cls.__name__, k)

    def __init__(self, name, bases, dct):
        self.__name__ = name
        self.type_name = name
        self.cls = bases[0]
        self.dct = dct
        self.init_dict(self)

    def __call__(self, *args, **kargs):
        result = self.cls(self, *args, **kargs)
        return result

    def __getattr__(self, name):
        if name[:2] != "__":
            return getattr(self.cls, name)
        else:
            raise AttributeError


# POSSIBLE TODO: a world doesn't know what is a player or a game...
# ... except for the resources and tech?!!! and alliances, ennemies
# rename "player" to "economy", "country", "tribe", "side",
# "force", "faction", "team"?)
class World(object):

    def __init__(self, default_triggers, seed=0):
        self.default_triggers = default_triggers
        self.id = self.get_next_id()
        worldrandom.seed(int(seed))
        self.time = 0
        self.squares = []
        self.active_objects = []
        self.players = []
        self.ex_players = []
        self.unit_classes = {}
        self.objects = {}
        self.harm_target_types = {}
        self._command_queue = Queue.Queue()

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict["_command_queue"]
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self._command_queue = Queue.Queue()

    def remove_links_for_savegame(self): # avoid pickle recursion problem
        for z in self.squares:
##            z.spt = {} # the shortest path cache may cause recursion problems if big enough (never happened, though)
            for e in z.exits:
                e.place = None

    def restore_links_for_savegame(self):
        for z in self.squares:
            for e in z.exits:
                e.place = z
        
    _next_id = 0 # reset ID for each world to avoid big numbers

    def get_next_id(self, increment=True):
        if increment:
            self._next_id += 1
            return str(self._next_id)
        else:
            return str(self._next_id + 1)

    # Why use a different id for orders: get_next_id() would have worked too,
    # but with higher risks of synchronization errors. This way is probably
    # more sturdy.

    _next_order_id = 0

    def get_next_order_id(self):
        self._next_order_id += 1
        return self._next_order_id

    current_player_number = 0

    def get_next_player_number(self):
        self.current_player_number += 1
        return self.current_player_number

    def clean(self):
        for p in self.players + self.ex_players:
            p.clean()
        for z in self.squares:
            z.clean()
        self.__dict__ = {}

    def _get_objects_values(self):
        names_to_check = ["x", "y", "hp", "cible"]
        if self.time == 0:
            names_to_check += ["id", "player"]
            objects_to_check = []
            for z in self.squares:
                objects_to_check += z.objects
        else:
            objects_to_check = self.active_objects
        for o in objects_to_check:
            for name in names_to_check:
                if hasattr(o, name):
                    value = getattr(o, name)
                    if name in ["cible", "player"]:
                        if hasattr(value, "id"):
                            value = value.id
                        else:
                            continue
                    yield "%s%s" % (name, value)

    def get_objects_string(self):
        return "".join(self._get_objects_values())

    def get_digest(self):
        d = md5(str(self.time))
        for p in self.players:
            d.update(str(len(p.units)))
        for z in self.squares:
            d.update(str(len(z.objects)))
        for ov in self._get_objects_values():
            d.update(ov)
        return d.hexdigest()

    _previous_slow_update = 0

    def update(self):
        # normal updates
        for p in self.players[:]:
            if p in self.players:
                try:
                    p.update()
                except:
                    exception("")
        for o in self.active_objects[:]:
            # much faster way to check if "o in self.active_objects":
            if o.place is not None:
                try:
                    o.update()
                except:
                    exception("")

        # slow updates (called every second)
        if self.time >= self._previous_slow_update + 1000:
            for o in self.active_objects[:]:
                # much faster way to check if "o in self.active_objects":
                if o.place is not None:
                    try:
                        o.slow_update()
                    except:
                        exception("")
            for p in self.players[:]:
                if p in self.players:
                    try:
                        p.slow_update()
                    except:
                        exception("")
            self._previous_slow_update += 1000

        # signal the end of the updates for this time
        self.time += VIRTUAL_TIME_INTERVAL
        for p in self.players[:]:
            if p.is_human():
                p.ready = False
            try:
                def _copy(l):
                    return set(copy.copy(o) for o in l)
                collision_debug = None
#                    collision_debug = copy.deepcopy(self.collision)
                if p.is_local_human(): # avoid unnecessary copies
                    if p.cheatmode:
                        observed_before_squares = self.squares
                    else:
                        observed_before_squares = p.observed_before_squares
                    p.push("voila", self.time,
                           _copy(p.memory), _copy(p.perception),
                           p.observed_squares.keys(),
                           observed_before_squares,
                           collision_debug)
            except:
                exception("")

        # if no "true" player is playing any more, end the game
        if not self.true_playing_players:
            for p in self.players:
                p.quit_game()

    ground = []
    global_food_limit = GLOBAL_FOOD_LIMIT

    # move the following methods to Map

    unit_base_classes = {"worker": Worker, "soldier": Soldier, "building": Building,
                         "effect": Effect,
                         "deposit": Deposit,
                         "upgrade": Upgrade, "ability": Ability}

    def unit_class(self, s):
        """Get a class-like unit generator from its name.
        
        Example: unit_class("peasant") to get a peasant generator

        At the moment, unit_classes contains also: upgrades, abilities...
        """
        if not self.unit_classes.has_key(s):
            try:
                base = self.unit_base_classes[get_rule(s, "class")[0]]
            except:
                if get_rule(s, "class") != ["race"]:
                    warning("no class defined for %s", s)
                self.unit_classes[s] = None
                return
            try:
                dct = get_rule_dict(s)
                t = Type(s, (base,), dct)
                if base is Upgrade:
                    t = base(s, dct) # factory-prototypes are only for units
                self.unit_classes[s] = t
            except:
                exception("problem with unit_class('%s')", s)
                self.unit_classes[s] = None
                return
        return self.unit_classes[s]

    def _get_classnames(self, condition):
        result = []
        for c in get_rule_classnames():
            uc = self.unit_class(c)
            if uc is not None and condition(uc):
                result.append(c)
        return result
        
    def get_makers(self, t):
        def can_make(uc, t):
            for a in ("can_build", "can_train", "can_upgrade_to"):
                if t in getattr(uc, a, []):
                    return True
        if t.__class__ != str:
            t = t.__name__
        return self._get_classnames(lambda uc: can_make(uc, t))

    def get_units(self):
        return self._get_classnames(lambda uc: issubclass(uc.cls, Unit))

    def get_soldiers(self):
        return self._get_classnames(lambda uc: issubclass(uc.cls, Soldier))

    def get_deposits(self, resource_index):
        return self._get_classnames(lambda uc: issubclass(uc.cls, Deposit) and uc.resource_type == resource_index)

    # map creation
    
    def _create_squares_and_grid(self):
        self.grid = {}
        for col in range(self.nb_columns):
            for row in range(self.nb_lines):
                square = Square(self, col, row, self.square_width)
                self.grid[square.name] = square
                self.grid[(col, row)] = square
                square.high_ground = square.name in self.high_grounds
        xmax = self.nb_columns * self.square_width
        res = COLLISION_RADIUS * 2 / 3
        self.collision = {"ground": collision.CollisionMatrix(xmax, res),
                          "air": collision.CollisionMatrix(xmax, res)}

    def _meadows(self):
        m = []
        for square in sorted([x for x in self.grid.keys() if isinstance(x, str)]):
            m.extend([square] * self.nb_meadows_by_square)
        m.extend(self.additional_meadows)
        for square in self.remove_meadows:
            if square in m:
                m.remove(square)
        return m

    def _create_resources(self):
        for z, cls, n in self.map_objects:
            C = self.unit_class(cls)
            if self.grid[z].can_receive("ground"): # avoids using the spiral
                C(self.grid[z], n)
        for z in self._meadows():
            Meadow(self.grid[z])

    def _arrange_resources_symmetrically(self):
        xc = self.nb_columns * 10 / 2
        yc = self.nb_lines * 10 / 2
        for z in self.squares:
            z.arrange_resources_symmetrically(xc, yc)

    def _we_places(self, i):
        t = string.ascii_lowercase
        col = t.find(i[0]) + 1
        if col == self.nb_columns:
            col = 0
        j = t[col] + i[1:]
        if not self.grid.has_key(j):
            map_error("", "The west-east passage starting from %s doesn't exist." % i)
        return self.grid[i].east_side(), self.grid[j].west_side()

    def _sn_places(self, i):
        line = int(i[1:]) + 1
        if line == self.nb_lines + 1:
            line = 1
        j = i[0] + str(line)
        if not self.grid.has_key(j):
            map_error("", "The south-north passage starting from %s doesn't exist." % i)
        return self.grid[i].north_side(), self.grid[j].south_side()

    def _create_passages(self):
        for t, squares in self.west_east:
            for i in squares:
                passage(self._we_places(i), t)
        for t, squares in self.south_north:
            for i in squares:
                passage(self._sn_places(i), t)
        self.g = {}
        for z in self.squares:
            for e in z.exits:
                self.g[e] = {}
                for f in z.exits:
                    if f is not e:
                        self.g[e][f] = int_distance(e.x, e.y, f.x, f.y)
                self.g[e][e.other_side] = 0

    def _build_map(self):
        self._create_squares_and_grid()
        self._create_resources()
        self._arrange_resources_symmetrically()
        self._create_passages()

    def _add_start_to(self, starts, resources, items, sq=None):
        def is_a_square(x):
            return x[0] in string.ascii_letters and x[1] in string.digits\
                   and (len(x) == 2 or len(x) == 3 and x[2] in string.digits)
        start = []
        multiplicator = 1
        for x in items:
            if is_a_square(x):
                sq = x
                multiplicator = 1
            elif x[0] == "-":
                start.append([None, x])
            elif re.match("[0-9]+$", x):
                multiplicator = int(x)
            else:
                start.extend([[sq, self.unit_class(x)]] * multiplicator)
                multiplicator = 1
        starts.append([resources, start, []])

    @property
    def nb_res(self):
        return int(get_rule("parameters", "nb_of_resource_types")[0])

    def _add_start(self, w, words, line):
        # get start type
        if w == "player":
            n = "players_starts"
        else:
            n = "computers_starts"
        # get resources
        starting_resources = []
        for c in words[1:1+self.nb_res]:
            try:
                starting_resources.append(to_int(c))
            except:
                map_error(line, "expected an integer but found %s" % c)
        # build start
        self._add_start_to(getattr(self, n), starting_resources, words[1+self.nb_res:])

    def _list_to_tree(self, words):
        cache = [[]]
        for w in words:
            if w == "(":
                cache.append([])
            elif w == ")":
                cache[-2].append(cache.pop())
            else:
                cache[-1].append(w)
        return cache[0]

    def _add_trigger(self, words):
        owners, condition, action = self._list_to_tree(words)
        if isinstance(owners, str):
            owners = [owners]
        for o in owners:
            if o == "computers":
                for s in self.computers_starts:
                    s[2].append([condition, action])
            elif o == "players":
                for s in self.players_starts:
                    s[2].append([condition, action])
            elif o == "all":
                for s in self.computers_starts + self.players_starts:
                    s[2].append([condition, action])
            elif o[:-1] == "computer":
                try:
                    self.computers_starts[int(o[-1:]) - 1][2].append([condition, action])
                except:
                    map_error("", "error in trigger for %s: unknown owner" % o)
            elif o[:-1] == "player":
                try:
                    self.players_starts[int(o[-1:]) - 1][2].append([condition, action])
                except:
                    map_error("", "error in trigger for %s: unknown owner" % o)
            else:
                map_error("", "error in trigger for %s: unknown owner" % o)

    def _load_map(self, map):
        
        def random_choice_repl(matchobj):
            return worldrandom.choice(matchobj.group(1).split("\n#end_choice\n"))

        def check_squares(squares):
            for sq in squares:
                if re.match("^[a-z]+[0-9]+$", sq) is None:
                    map_error(line, "%s is not a square" % sq)

        self.objective = []
        self.intro = []
        self.timer_coefficient = 1
        triggers = []

        self.map_objects = []

        self.computers_starts = []
        self.players_starts = []
        self.starting_units = []

        squares_words = ["starting_squares",
                         "additional_meadows", "remove_meadows",
                         "high_grounds"]

        self.square_width = 12 # default value
        self.nb_lines = 0
        self.nb_columns = 0
        self.nb_rows = 0 # deprecated (was incorrectly used for columns instead of lines)
        self.nb_meadows_by_square = 0

        self.west_east = []
        self.south_north = []

        # "squares words"
        self.starting_squares = []
        self.additional_meadows = []
        self.remove_meadows = []
        self.high_grounds = []

        self.starting_resources = [0 for _ in range(self.nb_res)]
        self.nb_players_min = 1
        self.nb_players_max = 1

        s = map.read() # "universal newlines"
        s = re.sub("(?m);.*$", "", s) # remove comments
        s = re.sub("(?m)^[ \t]*$\n", "", s) # remove empty lines
        s = re.sub(r"(?m)\\[ \t]*$\n", " ", s) # join lines ending with "\"
        s = s.replace("(", " ( ")
        s = s.replace(")", " ) ")
        s = re.sub(r"\s*\n\s*", r"\n", s) # strip lines
        s = re.sub(r"(?ms)^#random_choice\n(.*?)\n#end_random_choice$", random_choice_repl, s)
        s = re.sub(r"(?m)^(goldmine|wood)s\s+([0-9]+)\s+(.*)$", r"\1 \2 \3", s)
        s = re.sub(r"(south_north|west_east)_paths", r"\1 path", s)
        s = re.sub(r"(south_north|west_east)_bridges", r"\1 bridge", s)
        for line in s.split("\n"): # TODO: error msg
            words = line.strip().split()
            if not words:
                continue # empty line
            w = words[0]
            if w[0:1] == ";":
                continue # comment
            for _w in words[1:]:
                if w in ["south_north", "west_east"]:
                    continue # TODO: check that the exit type_name is defined in style
                for _w in _w.split(","):
                    if _w and _w[0] == "-": _w = _w[1:]
                    if re.match("^([a-z]+[0-9]+|[0-9]+(.[0-9]*)?|.[0-9]+)$", _w) is None and \
                       not hasattr(Player, "lang_" + _w) and \
                       _w not in get_rule_classnames() and \
                       _w not in get_ai_names() and \
                       _w not in ["(", ")", "all", "players", "computers"] and \
                       _w not in ORDERS_DICT:
                        map_error(line, "unknown: %s" % _w)
            if w in ["title", "objective", "intro"]:
                setattr(self, w, [int(x) for x in words[1:]]) # TODO: error msg (sounds)
            elif w in ["square_width", "nb_rows", "nb_columns", "nb_lines",
                       "nb_players_min", "nb_players_max", "scenario",
                       "nb_meadows_by_square",
                       "global_food_limit",
                       "timer_coefficient"]:
                try:
                    setattr(self, w, int(words[1]))
                    if w == "nb_rows":
                        self.nb_columns = self.nb_rows
                        warning("nb_rows is deprecated, use nb_columns instead")
                except:
                    map_error(line, "%s must be an integer" % w)
            elif w in ["south_north", "west_east"]:
                squares = words[2:]
                check_squares(squares)
                getattr(self, w).append((words[1], squares))
            elif w in squares_words:
                squares = words[1:]
                check_squares(squares)
                getattr(self, w).extend(squares)
            elif w in ["starting_resources"]:
                self.starting_resources = []
                for c in words[1:]:
                    try:
                        self.starting_resources.append(to_int(c))
                    except:
                        map_error(line, "expected an integer but found %s" % c)
            elif get_rule(w, "class") == ["deposit"]:
                for sq in words[2:]: # TODO: error msg (squares)
                    self.map_objects.append([sq, w, words[1]])
            elif w in ["starting_units"]:
                getattr(self, w).extend(words[1:]) # TODO: error msg (types)
            elif w in ["player", "computer_only", "computer"]:
                self._add_start(w, words, line)
            elif w == "trigger":
                triggers.append(words[1:])
            else:
                map_error(line, "unknown command: %s" % w)
        # build self.players_starts
        for sq in self.starting_squares:
            self._add_start_to(self.players_starts,
                               self.starting_resources, self.starting_units, sq)
        if self.nb_players_min > self.nb_players_max:
            map_error("", "nb_players_min > nb_players_max")
        if len(self.players_starts) < self.nb_players_max:
            map_error("", "not enough starting places for nb_players_max")
        # 2 multiplayer map types: with or without standard triggers
        # TODO: select in a menu: User Map Settings, melee, free for all, etc
        if not triggers and self.default_triggers:
            triggers = self.default_triggers
        for t in triggers:
            self._add_trigger(t)

    def load_and_build_map(self, map):
        if os.path.exists(MAPERROR_PATH):
            try:
                os.remove(MAPERROR_PATH)
            except:
                warning("cannot remove map error file")
        try:
            load_rules(res.get_text("rules", append=True), map.campaign_rules, map.additional_rules)
            load_ai(res.get_text("ai", append=True), map.campaign_ai, map.additional_ai)
            self._load_map(map)
            self.map = map
            self.square_width = int(self.square_width * 1000) # XXX 1000=PRECISION?
            self._build_map()
            if self.objective:
                self.introduction = [4020] + self.objective
            else:
                self.introduction = []
        except MapError, msg:
            warning("map error: %s", msg)
            self.map_error = "map error: %s" % msg
            return False
        return True

    def get_races(self):
        return [c for c in get_rule_classnames()
                if get_rule(c, "class") == ["race"]]

    # move this to Game?

    def current_nb_human_players(self):
        n = 0
        for p in self.players:
            if p.is_human():
                n += 1
        return n

    def true_players(self):
        return [p for p in self.players if not p.neutral]

    @property
    def true_playing_players(self):
        return [p for p in self.true_players() if p.is_playing]

    @property
    def food_limit(self):
        return self.global_food_limit

    def _add_player(self, player_class, client, start, *args):
        client.player = player_class(self, client, *args)
        self.players.append(client.player)
        client.player.start = start

    def populate_map(self, players, alliances, races=()):
        # add "true" (non neutral) players
        worldrandom.shuffle(self.players_starts)
        for client in players:
            start = self.players_starts.pop()
            if client.__class__.__name__ == "DummyClient":
                self._add_player(Computer, client, start, False)
            else:
                self._add_player(Human, client, start)
        # create the alliances
        if alliances:
            for p, pa in zip(self.players, alliances):
                for other, oa in zip(self.players, alliances):
                    if other is not p and oa == pa:
                        p.allied.append(other)
        else: # computer players are allied by default
            for p in self.players:
                if isinstance(p, Computer):
                    for other in self.players:
                        if other is not p and isinstance(other, Computer):
                            p.allied.append(other)
        # set the races for players
        if races:
            for p, pr in zip(self.players, races):
                if pr == "random_race":
                    p.race = worldrandom.choice(self.get_races())
                else:
                    p.race = pr
        # add "neutral" (independent) computers
        for start in self.computers_starts:
            self._add_player(Computer, worldclient.DummyClient(), start, True)
        # init all players positions
        for player in self.players:
            player.init_position()
        self.admin = players[0] # define get_admin()?

    def loop(self):
        while(self.__dict__): # cf clean()
            if not self._command_queue.empty():
                player, order = self._command_queue.get()
                try:
                    player.execute_command(order)
                except:
                    exception("")
            else:
                time.sleep(.01)

    def queue_command(self, player, order):
        self._command_queue.put((player, order))


class MapError(Exception):

    pass


def map_error(line, msg):
    w = 'error in "%s": %s' % (line, msg)
    try:
        open(MAPERROR_PATH, "w").write(w)
    except:
        warning("could not write in %s", MAPERROR_PATH)
    raise MapError(w)
