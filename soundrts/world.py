import copy
from soundrts.lib.sound import distance
from soundrts.lib.nofloat import square_of_distance
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import os.path
import Queue
import random
import re
import string
import time

from lib import chronometer as chrono
from lib import collision
from definitions import rules, get_ai_names, load_ai, VIRTUAL_TIME_INTERVAL
from lib.log import warning, exception, info
from lib.nofloat import to_int, int_distance, PRECISION
import msgparts as mp
from paths import MAPERROR_PATH
import res
from worldability import Ability
from worldclient import DummyClient
from worldentity import COLLISION_RADIUS
from worldexit import passage
from worldorders import ORDERS_DICT
from worldplayerbase import Player, normalize_cost_or_resources, A
from worldplayercomputer import Computer
from worldplayercomputer2 import Computer2
from worldresource import Deposit, Meadow
from worldroom import Square
from worldunit import Unit, Worker, Soldier, Building, _Building, Effect, ground_or_air
from worldupgrade import Upgrade


GLOBAL_FOOD_LIMIT = 80
PROFILE = False

def check_squares(line, squares):
    for sq in squares:
        if re.match("^[a-z]+[0-9]+$", sq) is None:
            map_error(line, "%s is not a square" % sq)


class Type(object):

    def __repr__(self):
        return "<Type '%s'>" % self.type_name

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
        if "cost" not in dct and hasattr(self.cls, "cost"):
            dct["cost"] = [0] * rules.get("parameters", "nb_of_resource_types")
        if "sight_range" in dct and dct["sight_range"] == 1 * PRECISION:
            dct["sight_range"] = 12 * PRECISION
            dct["bonus_height"] = 1
            info("in %s: replacing sight_range 1 with sight_range 12 and bonus_height 1", name)
        if "special_range" in dct:
            del dct["special_range"]
            dct["range"] = 12 * PRECISION
            dct["minimal_range"] = 4 * PRECISION 
            dct["is_ballistic"] = 1
            info("in %s: replacing special_range 1 with range 12, minimal_range 4 and is_ballistic 1", name)
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


class World(object):

    def __init__(self, default_triggers, seed=0, must_apply_equivalent_type=False):
        self.default_triggers = default_triggers
        self.seed = seed
        self.must_apply_equivalent_type = must_apply_equivalent_type
        self.id = self.get_next_id()
        self.random = random.Random()
        self.random.seed(int(seed))
        self.time = 0
        self.squares = []
        self.active_objects = []
        self.players = []
        self.ex_players = []
        self.unit_classes = {}
        self.objects = {}
        self.harm_target_types = {}
        self._command_queue = Queue.Queue()

        # "map" properties

        self.objective = []
        self.intro = []
        self.timer_coefficient = 1

        self.map_objects = []

        self.computers_starts = []
        self.players_starts = []
        self.starting_units = []
        self.starting_resources = [] # just for the editor
        self.specific_starts = [] # just for the editor

        self.square_width = 12 # default value
        self.nb_lines = 0
        self.nb_columns = 0
        self.nb_rows = 0 # deprecated (was incorrectly used for columns instead of lines)
        self.nb_meadows_by_square = 0

        self.west_east = []
        self.south_north = []

        self.terrain = {}
        self.terrain_speed = {}
        self.terrain_cover = {}
        self.water_squares = set()
        self.no_air_squares = set()
        self.ground_squares = set()

        # "squares words"
        self.starting_squares = []
        self.additional_meadows = []
        self.remove_meadows = []
        self.high_grounds = []

        self.nb_players_min = 1
        self.nb_players_max = 1

    def __repr__(self):
        return "World(%s)" % self.seed

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict["_command_queue"]
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self._command_queue = Queue.Queue()

    def remove_links_for_savegame(self): # avoid pickle recursion problem
        for z in self.squares:
            for e in z.exits:
                e.place = None

    def restore_links_for_savegame(self):
        for z in self.squares:
            for e in z.exits:
                e.place = z
        self.set_neighbors()

    @property
    def turn(self):
        return self.time / VIRTUAL_TIME_INTERVAL

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

    def get_objects(self, x, y, radius, filter=lambda x: True):
        radius_2 = radius * radius
        return [o for z in self.squares for o in z.objects
                if filter(o) and square_of_distance(x, y, o.x, o.y) <= radius_2]

    def get_objects2(self, x, y, radius, filter=lambda x: True, players=None):
        if not players:
            players = self.players
        radius_2 = radius * radius
        return [o for p in players for o in p._potential_neighbors(x, y)
                if filter(o) and square_of_distance(x, y, o.x, o.y) <= radius_2]

    def get_place_from_xy(self, x, y):
        return self.grid.get((x / self.square_width,
                              y / self.square_width))

    def get_subsquare_id_from_xy(self, x, y):
        return x * 3 / self.square_width, y * 3 / self.square_width

    def can_harm(self, unit_type_name, other_type_name): 
        try:
            return self.harm_target_types[(unit_type_name, other_type_name)]
        except:
            unit = self.unit_class(unit_type_name)
            other = self.unit_class(other_type_name)
            if other is None:
                result = False
            else:
                result = True
                for t in unit.harm_target_type:
                    if t == "healable" and not other.is_healable or \
                       t == "building" and not other.is_a_building or \
                       t in ("air", "ground") and ground_or_air(other.airground_type) != t or \
                       t == "unit" and not other.is_a_unit or \
                       t == "undead" and not other.is_undead:
                        result = False
                        break
            self.harm_target_types[(unit_type_name, other_type_name)] = result
            return result

    def _free_memory(self):
        for p in self.players + self.ex_players:
            p.clean()
        for z in self.squares:
            z.clean()
        self.__dict__ = {}

    def _get_objects_values(self):
        yield str(self.random.getstate())
##        yield "starting_squares = {}".format(self.starting_squares)
##        names_to_check = ["type_name", "id", "x", "y", "hp", "action_target"]
##        if self.time == 0:
##            names_to_check += ["id", "player"]
##            objects_to_check = []
##            for z in self.squares:
##                objects_to_check += z.objects
##        else:
##            objects_to_check = self.active_objects
##        yield str(self.starting_squares)
##        for o in objects_to_check:
##            if getattr(o, "orders", False):
##                yield o.orders[0].keyword
##                if o.orders[0].keyword == "auto_explore":
##                    yield "already=" + str(sorted(list(o.player._already_explored),key=lambda x: getattr(x, "name", None)))
##                    yield "_places_to_explore=" + str(o.player._places_to_explore)
##            for name in names_to_check:
##                if hasattr(o, name):
##                    value = getattr(o, name)
##                    if name in ["action_target", "player"]:
##                        if hasattr(value, "id"):
##                            value = value.id
##                            if value in self.objects:
##                                if self.objects[value].__class__.__name__ == "Exit":
##                                    value = value, self.objects[value]
##                                else:
##                                    value = value, self.objects[value].__class__.__name__
##                        else:
##                            continue
##                    yield "%s=%s" % (name, value)
##            yield ""

    def get_objects_string(self):
        return "\n".join(self._get_objects_values())

    def get_digest(self):
        d = md5(str(self.time))
        for p in self.players:
            d.update(str(len(p.units)))
        for z in self.squares:
            d.update(str(len(z.objects)))
        for ov in self._get_objects_values():
            d.update(ov)
        return d.hexdigest()

    def _update_buckets(self):
        for p in self.players:
            p._buckets = {}
            for u in p.units:
                k = (u.x / A, u.y / A)
                try:
                    p._buckets[k].append(u)
                except:
                    p._buckets[k] = [u]

    def _update_cloaking(self):
        for p in self.players:
            for u in p.units:
                if u.is_cloakable:
                    u.is_cloaked = False
        for p in self.players:
            for u in p.units:
                if u.is_a_cloaker:
                    radius2 = u.cloaking_range * u.cloaking_range
                    for vp in p.allied:
                        for vu in vp._potential_neighbors(u.x, u.y):
                            if not vu.is_cloakable or vu.is_cloaked: continue
                            if square_of_distance(vu.x, vu.y, u.x, u.y) < radius2:
                                vu.is_cloaked = True
                                continue

    def _update_detection(self):
        for p in self.players:
            p.detected_units = set()
        for p in self.players:
            for u in p.units:
                if u.is_a_detector:
                    radius2 = u.detection_range * u.detection_range
                    for e in self.players:
                        if e in p.allied: continue
                        for iu in e._potential_neighbors(u.x, u.y):
                            if not (iu.is_invisible or iu.is_cloaked): continue
                            if iu in p.detected_units: continue
                            if square_of_distance(iu.x, iu.y, u.x, u.y) < radius2:
                                for a in p.allied_vision:
                                    a.detected_units.add(iu)
                                continue

    previous_state = (0, "")

    def _record_sync_debug_info(self):
        try:
            self.previous_previous_state = self.previous_state
        except AttributeError:
            pass
        self.previous_state = self.time, self.get_objects_string()

    def cpu_intensive_players(self):
        return [p for p in self.players if p.is_cpu_intensive]

    def _update_terrain(self):
        for s in self.squares:
            if s.type_name in ["", "_meadows", "_forest", "_dense_forest"]:
                s.update_terrain()

    _previous_slow_update = 0

    def update(self):
        chrono.start("update")
        # normal updates
        self._update_terrain()
        self._update_buckets()
        self._update_cloaking()
        self._update_detection()
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

        # remove from perception the objects deleted during this turn
        for p in self.players:
            for o in p.perception.copy():
                if o.place is None:
                    p.perception.remove(o)

        chrono.stop("update")
        self._record_sync_debug_info()

        # signal the end of the updates for this time
        self.time += VIRTUAL_TIME_INTERVAL
        for p in self.players[:]:
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
                           p.observed_squares,
                           observed_before_squares,
                           collision_debug)
            except:
                exception("")

        # if no "true" player is playing any more, end the game
        if not self.true_playing_players:
            for p in self.players:
                p.quit_game()

    global_food_limit = GLOBAL_FOOD_LIMIT

    # move the following methods to Map

    unit_base_classes = {"worker": Worker, "soldier": Soldier,
                         "building": Building,
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
                base = self.unit_base_classes[rules.get(s, "class")[0]]
            except:
                if rules.get(s, "class") != ["faction"]:
                    warning("no class defined for %s", s)
                self.unit_classes[s] = None
                return
            try:
                dct = rules.get_dict(s)
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
        for c in rules.classnames():
            uc = self.unit_class(c)
            if uc is not None and condition(uc):
                result.append(c)
        return result
        
    def get_makers(self, t):
        def can_make(uc, t):
            for a in ("can_build", "can_train", "can_upgrade_to", "can_research"):
                if t in getattr(uc, a, []):
                    return True
            for ability in getattr(uc, "can_use", []):
                effect = rules.get(ability, "effect")
                if effect and "summon" in effect[:1] and t in effect:
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

    def set_neighbors(self):
        for square in set(self.grid.values()):
            square.set_neighbors()

    def _create_squares_and_grid(self):
        self.grid = {}
        for col in range(self.nb_columns):
            for row in range(self.nb_lines):
                square = Square(self, col, row, self.square_width)
                self.grid[square.name] = square
                self.grid[(col, row)] = square
                square.high_ground = square.name in self.high_grounds
                if square.name in self.terrain:
                    square.type_name = self.terrain[square.name]
                if square.name in self.terrain_speed:
                    square.terrain_speed = self.terrain_speed[square.name]
                if square.name in self.terrain_cover:
                    square.terrain_cover = self.terrain_cover[square.name]
                if square.name in self.water_squares:
                    square.is_water = True
                    square.is_ground = square.name in self.ground_squares
                if square.name in self.no_air_squares:
                    square.is_air = False
        self.set_neighbors()
        xmax = self.nb_columns * self.square_width
        res = COLLISION_RADIUS * 2 / 3
        self.collision = {"ground": collision.CollisionMatrix(xmax, res),
                          "air": collision.CollisionMatrix(xmax, res)}
        self.collision["water"] = self.collision["ground"]

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
                resource = C(self.grid[z], n)
                resource.building_land = Meadow(self.grid[z])
                resource.building_land.delete()
        for z in self._meadows():
            Meadow(self.grid[z])

    def _arrange_resources_symmetrically(self):
        xc = self.nb_columns * 10 / 2
        yc = self.nb_lines * 10 / 2
        for z in self.squares:
            z.arrange_resources_symmetrically(xc, yc)

    def _we_places(self, i):
        is_a_portal = False
        t = string.ascii_lowercase
        col = t.find(i[0]) + 1
        if col == self.nb_columns:
            col = 0
            is_a_portal = True
        j = t[col] + i[1:]
        if not self.grid.has_key(j):
            map_error("", "The west-east passage starting from %s doesn't exist." % i)
        return self.grid[i].east_side(), self.grid[j].west_side(), is_a_portal

    def _sn_places(self, i):
        is_a_portal = False
        line = int(i[1:]) + 1
        if line == self.nb_lines + 1:
            line = 1
            is_a_portal = True
        j = i[0] + str(line)
        if not self.grid.has_key(j):
            map_error("", "The south-north passage starting from %s doesn't exist." % i)
        return self.grid[i].north_side(), self.grid[j].south_side(), is_a_portal

    def _ground_graph(self):
        g = {}
        for z in self.squares:
            for e in z.exits:
                g[e] = {}
                for f in z.exits:
                    if f is not e:
                        g[e][f] = int_distance(e.x, e.y, f.x, f.y)
                g[e][e.other_side] = 0
        return g

    def _air_graph(self):
        g = {}
        for z in self.squares:
            g[z] = {}
            if not z.is_air:
                continue
            # This is not perfect. Some diagonals will be missing.
            if [z2 for z2 in z.strict_neighbors if not z2.is_air]:
                n = z.strict_neighbors
            else:
                n = z.neighbors
            for z2 in n:
                if not z2.is_air:
                    continue
                g[z][z2] = int_distance(z.x, z.y, z2.x, z2.y)
        return g  

    def _water_graph(self):
        g = {}
        for z in self.squares:
            g[z] = {}
            if not z.is_water:
                continue
            # This is not perfect. Some diagonals will be missing.
            if [z2 for z2 in z.strict_neighbors if not z2.is_water]:
                n = z.strict_neighbors
            else:
                n = z.neighbors
            for z2 in n:
                if not z2.is_water:
                    continue
                g[z][z2] = int_distance(z.x, z.y, z2.x, z2.y)
        return g  
                
    def _create_passages(self):
        for t, squares in self.west_east:
            for i in squares:
                passage(self._we_places(i), t)
        for t, squares in self.south_north:
            for i in squares:
                passage(self._sn_places(i), t)

    def _create_graphs(self):
        self.g = {}
        self.g["ground"] = self._ground_graph()
        self.g["air"] = self._air_graph()
        self.g["water"] = self._water_graph()

    def _build_map(self):
        self._create_squares_and_grid()
        self._create_resources()
        self._arrange_resources_symmetrically()
        self._create_passages()
        self._create_graphs()

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
        return rules.get("parameters", "nb_of_resource_types")

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

    def random_choice_repl(self, matchobj):
        return self.random.choice(matchobj.group(1).split("\n#end_choice\n"))

    def _load_map(self, map):
        triggers = []
        starting_resources = [0 for _ in range(self.nb_res)]

        squares_words = ["starting_squares",
                         "additional_meadows", "remove_meadows",
                         "high_grounds"]

        s = map.read() # "universal newlines"
        s = re.sub("(?m);.*$", "", s) # remove comments
        s = re.sub("(?m)^[ \t]*$\n", "", s) # remove empty lines
        s = re.sub(r"(?m)\\[ \t]*$\n", " ", s) # join lines ending with "\"
        s = s.replace("(", " ( ")
        s = s.replace(")", " ) ")
        s = re.sub(r"\s*\n\s*", r"\n", s) # strip lines
        s = re.sub(r"(?ms)^#random_choice\n(.*?)\n#end_random_choice$", self.random_choice_repl, s)
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
                if w in ["south_north", "west_east", "terrain", "speed", "cover"]:
                    continue # TODO: check that the exit type_name is defined in style
                for _w in _w.split(","):
                    if _w and _w[0] == "-": _w = _w[1:]
                    if re.match("^([a-z]+[0-9]+|[0-9]+(.[0-9]*)?|.[0-9]+)$", _w) is None and \
                       not hasattr(Player, "lang_" + _w) and \
                       _w not in rules.classnames() and \
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
                check_squares(line, squares)
                getattr(self, w).append((words[1], squares))
            elif w in squares_words:
                squares = words[1:]
                check_squares(line, squares)
                getattr(self, w).extend(squares)
            elif w in ["starting_resources"]:
                self.starting_resources = " ".join(words[1:]) # just for the editor
                starting_resources = []
                for c in words[1:]:
                    try:
                        starting_resources.append(to_int(c))
                    except:
                        map_error(line, "expected an integer but found %s" % c)
            elif rules.get(w, "class") == ["deposit"]:
                for sq in words[2:]: # TODO: error msg (squares)
                    self.map_objects.append([sq, w, words[1]])
            elif w in ["starting_units"]:
                getattr(self, w).extend(words[1:]) # TODO: error msg (types)
            elif w in ["player", "computer_only", "computer"]:
                self.specific_starts.append(" ".join(words)) # just for the editor
                self._add_start(w, words, line)
            elif w == "trigger":
                triggers.append(words[1:])
            elif w == "terrain":
                t = words[1]
                squares = words[2:]
                check_squares(line, squares)
                for sq in squares:
                    self.terrain[sq] = t
            elif w == "speed":
                t = tuple(int(float(x) * 100) for x in words[1:3])
                squares = words[3:]
                check_squares(line, squares)
                for sq in squares:
                    self.terrain_speed[sq] = t
            elif w == "cover":
                t = tuple(int(float(x) * 100) for x in words[1:3])
                squares = words[3:]
                check_squares(line, squares)
                for sq in squares:
                    self.terrain_cover[sq] = t
            elif w == "water":
                squares = words[1:]
                check_squares(line, squares)
                self.water_squares.update(squares)
            elif w == "ground":
                squares = words[1:]
                check_squares(line, squares)
                self.ground_squares.update(squares)
            elif w == "no_air":
                squares = words[1:]
                check_squares(line, squares)
                self.no_air_squares.update(squares)
            else:
                map_error(line, "unknown command: %s" % w)
        # build self.players_starts
        for sq in self.starting_squares:
            self._add_start_to(self.players_starts,
                               starting_resources, self.starting_units, sq)
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
            rules.load(res.get_text_file("rules", append=True), map.campaign_rules, map.additional_rules)
            load_ai(res.get_text_file("ai", append=True), map.campaign_ai, map.additional_ai)
            self._load_map(map)
            self.map = map
            self.square_width = int(self.square_width * PRECISION)
            self._build_map()
        except MapError, msg:
            warning("map error: %s", msg)
            self.map_error = "map error: %s" % msg
            return False
        return True

    @property
    def factions(self):
        return [c for c in rules.classnames()
                if rules.get(c, "class") == ["faction"]]

    # move this to Game?

    def current_nb_human_players(self):
        n = 0
        for p in self.players:
            if p.is_human:
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

    def _add_player(self, client, start):
        player = client.player_class(self, client)
        player.start = start
        client.player = player
        self.players.append(player)

    def _create_true_players(self, players, random_starts):
        starts = self.players_starts[:]
        if random_starts:
            self.random.shuffle(starts)
        for client in players:
            start = starts.pop(0)
            self._add_player(client, start)
        for p in self.players:
            p.init_alliance()

    def _create_neutrals(self):
        for start in self.computers_starts:
            self._add_player(DummyClient(neutral=True), start)

    def populate_map(self, players, random_starts=True):
        self._create_true_players(players, random_starts)
        self._create_neutrals()
        for player in self.players:
            player.init_position()

    def stop(self):
        self._must_loop = False

    def _loop(self):
        self._must_loop = True
        while(self._must_loop):
            if not self._command_queue.empty():
                player, order = self._command_queue.get()
                try:
                    if player is None:
                        order()
                    else:
                        player.execute_command(order)
                except:
                    exception("")
            else:
                time.sleep(.001)

    def loop(self):
        if PROFILE:
            import cProfile
            cProfile.runctx("self._loop()", globals(), locals(), "world_profile.tmp")
            import pstats
            for n in ("world_profile.tmp", ):
                p = pstats.Stats(n)
                p.strip_dirs()
                p.sort_stats('time', 'cumulative').print_stats(30)
                p.print_callers(30)
                p.print_callees(20)
                p.sort_stats('cumulative').print_stats(50)
                p.print_callers(100)
                p.print_callees(100)
        else:
            self._loop()
        self._free_memory()

    def queue_command(self, player, order):
        self._command_queue.put((player, order))

    def save_map(self, filename):
        def _sorted(squares):
            return sorted(squares, key=lambda n: (n[0], int(n[1:])))
        def res():
            return sorted(set((o.type_name, o.qty / PRECISION) for s in set(self.grid.values()) for o in s.objects if getattr(o, "resource_type", None) is not None),
                          key=lambda x: (x[0], -x[1]))
        with open(filename, "w") as f:
            f.write("title %s\n" % " ".join(map(str, self.title)))
            f.write("objective %s\n" % " ".join(map(str, self.objective)))
            f.write("\n")
            f.write("square_width %s\n" % (self.square_width / PRECISION))
            f.write("nb_columns %s\n" % self.nb_columns)
            f.write("nb_lines %s\n" % self.nb_lines)
            f.write("\n")
            f.write("nb_players_min %s\n" % self.nb_players_min)
            f.write("nb_players_max %s\n" % self.nb_players_max)
            f.write("starting_squares %s\n" % " ".join(_sorted(self.starting_squares)))
            f.write("starting_units %s\n" % " ".join(self.starting_units))
            f.write("starting_resources %s\n" % self.starting_resources)
            for line in self.specific_starts:
                f.write(line + "\n")
            f.write("\n")
            for t, q in res():
                squares = _sorted(s.name for s in set(self.grid.values()) for o in s.objects if o.type_name == t and o.qty / PRECISION == q)
                f.write("%s %s %s\n" % (t, q, " ".join(squares)))
            f.write("\nnb_meadows_by_square 0\n")
            for n in sorted(set([s.nb_meadows for s in self.grid.values() if s.nb_meadows])):
                squares = _sorted([s.name for s in set(self.grid.values()) if s.nb_meadows == n])
                if n == 1:
                    f.write("; 1 meadow\n")
                else:
                    f.write("; %s meadows\n" % n)
                for _ in range(n):
                    f.write("additional_meadows %s\n" % " ".join(squares))
            f.write("\n")
            for t in sorted(set([s.type_name for s in self.grid.values() if s.type_name])):
                squares = _sorted([s.name for s in set(self.grid.values()) if s.type_name == t])
                f.write("terrain %s %s\n" % (t, " ".join(squares)))
            squares = _sorted([s.name for s in set(self.grid.values()) if s.high_ground])
            f.write("high_grounds %s\n" % " ".join(squares))
            squares = _sorted([s.name for s in set(self.grid.values()) if s.is_water])
            f.write("water %s\n" % " ".join(squares))
            squares = _sorted([s.name for s in set(self.grid.values()) if s.is_ground and s.is_water])
            f.write("ground %s\n" % " ".join(squares))
            squares = _sorted([s.name for s in set(self.grid.values()) if not s.is_air])
            f.write("no_air %s\n" % " ".join(squares))
            for t in sorted(set([s.terrain_cover for s in self.grid.values() if s.terrain_cover != (0, 0)])):
                squares = _sorted([s.name for s in set(self.grid.values()) if s.terrain_cover == t])
                f.write("cover %s %s\n" % (" ".join(map(lambda x: str(x / 100.0), t)), " ".join(squares)))
            for t in sorted(set([s.terrain_speed for s in self.grid.values() if s.terrain_speed != (100, 100)])):
                squares = _sorted([s.name for s in set(self.grid.values()) if s.terrain_speed == t])
                f.write("speed %s %s\n" % (" ".join(map(lambda x: str(x / 100.0), t)), " ".join(squares)))
            f.write("\n")
            we = dict()
            sn = dict()
            for s in set(self.grid.values()):
                for e in s.exits:
                    o = e.other_side.place
                    delta = o.col - s.col, o.row - s.row
                    if delta == (1, 0):
                        if e.type_name not in we:
                            we[e.type_name] = []
                        we[e.type_name].append(s.name)
                    elif delta == (0, 1):
                        if e.type_name not in sn:
                            sn[e.type_name] = []
                        sn[e.type_name].append(s.name)
            for tn in we:
                f.write("west_east %s %s\n" % (tn, " ".join(_sorted(we[tn]))))
            for tn in sn:
                f.write("south_north %s %s\n" % (tn, " ".join(_sorted(sn[tn]))))


class MapError(Exception):

    pass


def map_error(line, msg):
    w = 'error in "%s": %s' % (line, msg)
    try:
        open(MAPERROR_PATH, "w").write(w)
    except:
        warning("could not write in %s", MAPERROR_PATH)
    raise MapError(w)
