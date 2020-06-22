import copy
import inspect
import re
from typing import Dict, List

from .definitions import rules, style, MAX_NB_OF_RESOURCE_TYPES
from .lib import group
from .lib.log import info, warning, exception
from .lib.msgs import encode_msg, nb2msg
from .lib.nofloat import square_of_distance, to_int, PRECISION
from . import msgparts as mp
from .worldentity import NotEnoughSpaceError, Entity
from .worldresource import Corpse
from .worldunit import BuildingSite, Soldier, Unit
from .worldupgrade import Upgrade


A = 12 * PRECISION # bucket side length
VERY_SLOW = int(.01 * PRECISION)


class ZoomTarget:

    collision = 0
    radius = 0

    def __init__(self, i, player):
        self.id = i
        _, place_id, x, y = i.split("-")
        self.x = int(x)
        self.y = int(y)
        self.place = player.get_object_by_id(place_id)
        self.title = self.place.title # TODO: full zoom title

    def __eq__(self, other):
        if isinstance(other, ZoomTarget):
            return self.x, self.y == other.x, other.y

    def __ne__(self, other): return not self.__eq__(other)

    @property
    def building_land(self):
        for o in self.place.objects:
            if o.is_a_building_land and self.contains(o.x, o.y):
                return o
        return self.place.building_land

    def contains(self, x, y):
        subsquare = self.place.world.get_subsquare_id_from_xy
        return subsquare(self.x, self.y) == subsquare(x, y)


class Objective:

    def __init__(self, number, description):
        self.number = number
        self.description = description


def normalize_cost_or_resources(lst):
    n = rules.get("parameters", "nb_of_resource_types")
    while len(lst) < n:
        lst += [0]
    while len(lst) > n:
        del lst[-1]


class Player:

    cheatmode = False
    used_food = 0
    food = 0
    observer_if_defeated = False
    has_victory = False
    has_been_defeated = False
    faction = "human_faction"
    memory_duration = 3 * 60 * 1000 # 3 minutes of world time

    group = ()
    group_had_enough_mana = False # used to warn if not enough mana

    is_cpu_intensive = False
    smart_units = False

    groups: Dict[str, List[Unit]] = {}

    def __init__(self, world, client):
        self.neutral = client.neutral
        self.faction = world.random.choice(world.factions) \
                       if client.faction  == "random_faction" \
                       else client.faction
        self.allied = [self]
        if not self.neutral:
            self.number = world.get_next_player_number()
        else:
            self.number = None
        self.perception = set()
        self.memory = set()
        self._memory_index = {}
        self.id = world.get_next_id()
        self.world = world
        self.client = client
        self.ia_start_index = 0
        self.ia_index = 0
        self.objectives = {}
        self.units = []
        self.budget = []
        self.upgrades = []
        self.forbidden_techs = []
        self.observed_before_squares = set()
        self.observed_squares = set()
        self.observed_objects = {}
        self.detected_units = set()
        self.allied_control = (self, )
        self._known_enemies = {}
        self._known_enemies_time = {}
        self._enemy_menace = {}
        self._enemy_menace_time = {}
        self._subsquare_threat = {}

    @property
    def name(self):
        if self.neutral:
            return []
        else:
            return self.client.name

    @property
    def is_playing(self):
        return not (self.has_victory or self.has_been_defeated)

    def raise_threat(self, subsquare, delta):
        try:
            self._subsquare_threat[subsquare] += delta
        except:
            self._subsquare_threat[subsquare] = delta

    def _get_threat(self, subsquare):
        try:
            return self._subsquare_threat[subsquare]
        except:
            return 0

    def get_safest_subsquare(self, place):
        x = place.x * 3 // self.world.square_width
        y = place.y * 3 // self.world.square_width
        candidates = list((x + dx, y + dy) for dx in (0, 1, -1) for dy in (0, 1, -1))
        sub = sorted(candidates, key=self._get_threat)[0]
        return (sub[0] * self.world.square_width // 3 + self.world.square_width // 6,
                sub[1] * self.world.square_width // 3 + self.world.square_width // 6)
    
    def known_enemies(self, place):
        # assert: "memory is not included"
        # warning: memory objects are not in place.objects
        if self._known_enemies_time.get(place) != self.world.time:
            enemy_units = []
            for e in self.world.players:
                if e.player_is_an_enemy(self):
                    enemy_units.extend(e.units)
            self._known_enemies[place] = [u for u in
                set(self.perception).intersection(enemy_units).intersection(place.objects)
                if u.is_vulnerable and not u.is_inside]
            self._known_enemies_time[place] = self.world.time
        else:
            # eventually remove deleted units
            self._known_enemies[place] = [u for u in self._known_enemies[place] if u.place]
        return self._known_enemies[place]

    @property
    def allied_victory(self):
        return self.allied

    @property
    def allied_vision(self):
        return self.allied

    def slow_update(self):
        self.free_project_resources_if_no_worker_on_project()
        self.run_triggers()

    def _update_storage_bonus(self):
        self.storage_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        for u in self.units:
            for res, bonus in enumerate(u.storage_bonus):
                self.storage_bonus[res] = max(self.storage_bonus[res], bonus)

    def _update_allied_upgrades(self):
        for p in self.allied:
            for upgrade_name in p.upgrades:
                while self.level(upgrade_name) < p.level(upgrade_name):
                    self.world.unit_class(upgrade_name).upgrade_player(self)

    def _potential_neighbors(self, x, y):
        result = []
        x = x // A
        y = y // A
        for dx in [0, 1, -1]:
            for dy in [0, 1, -1]:
                k = x + dx, y + dy
                # probably faster to check the key instead of catching a KeyError exception
                # (most buckets are empty)
                if k in self._buckets:
                    result.extend(self._buckets[k])
        return result
        
    def _is_seeing(self, u):
        if (u.is_invisible or u.is_cloaked) and u not in self.detected_units:
            return
        x = u.x
        y = u.y
        for avp in self.allied_vision:
            for avu in self._potential_neighbors(x, y):
                radius2 = avu.sight_range * avu.sight_range
                if (square_of_distance(avu.x, avu.y, x, y) < radius2
                    and (avu.sight_range >= self.world.square_width
                         or u.place in avu.get_observed_squares())):
                    return True

    def _team_has_lost(self):
        for p in self.allied_vision:
            if not p.has_been_defeated:
                return False
        return True

    def _update_perception(self):
        if self.cheatmode or self._team_has_lost():
            self.observed_squares = set(self.world.squares)
            self.perception = set()
            for s in self.world.squares:
                self.perception.update(s.objects)
            return
        # init
        self.perception = set()
        self.observed_squares = set()
        partially_observed_squares = set()
        # terrain, exits, resources
        for p in self.allied_vision:
            done = []
            for u in p.units:
                k = (u.is_inside, u.sight_range  < self.world.square_width, u.height, u.place)
                if k in done: continue
                self.observed_squares.update(u.get_observed_squares(strict=True))
                partially_observed_squares.update(u.get_observed_squares(partial=True))
                done.append(k)
        partially_observed_squares -= self.observed_squares
        for s in self.observed_squares:
            for o in s.objects:
                if o.player is None:
                    self.perception.add(o)
        # partially observed squares show the terrain as memory with a fog of war warning
        for s in partially_observed_squares:
            for o in s.objects:
                if o.player is None:
                    if self._is_seeing(o):
                        self.perception.add(o)
                    else:
                        self._memorize(o)
        self.observed_before_squares.update(partially_observed_squares)
        # objects revealed by their actions
        for p in self.allied_vision:
            for o in list(p.observed_objects.keys()):
                # remove old observed objects and deleted objects
                if (p.observed_objects[o] < self.world.time
                    or o.place is None):
                    del p.observed_objects[o]
            self.perception.update(list(p.observed_objects.keys()))
        # sight
        for p in self.world.players:
            if p in self.allied_vision:
                self.perception.update(p.units)
            else:
                for u in p.units:
                    if self._is_seeing(u):
                        self.perception.add(u)
        # remove units inside buildings from perception
        for o in self.perception.copy():
            if o.is_inside and o not in self.units:
                self.perception.remove(o)

    def _update_memory(self, previous_perception):
        self.observed_before_squares.update(self.observed_squares)
        for m in self.memory.copy():
            # forget units reappearing elsewhere
            # forget deleted units
            # forget old memories of mobile units
            # forget if in an observed square
            if (m.initial_model in self.perception
                or m.initial_model.place is None # ideally: and self.have_an_observer_in_sight_range(m)
                or m.initial_model.speed and m.time_stamp + self.memory_duration < self.world.time
                or m.place in self.observed_squares):
                self._forget(m)
        # memorize disappeared units
        # don't memorize deleted units
        # don't memorize invisible or cloaked units (confusing)
        for o in previous_perception - self.perception:
            if o.is_invisible or o.is_cloaked: continue
            if o.place is not None:
                self._memorize(o)

    def _update_perception_and_memory(self):
        previous_perception = self.perception.copy()
        self._update_perception()
        self._update_memory(previous_perception)

    def _update_menace(self):
        self._menace = sum(u.menace for u in self.units if u.speed > 0 and isinstance(u, Soldier))

    def _update_enemy_menace_and_presence_and_corpses(self):
        self._enemy_menace = {}
        self._enemy_presence = []
        self._places_with_corpses = set()
        self._places_with_friends = set()
        self._cataclysmic_places = set()
        for l in (self.perception, self.memory):
            for o in sorted(l, key=lambda x: x.id): # sort to avoid desync error
                place = o.place
                if not hasattr(place, "exits"):
                    continue
                if self.is_an_enemy(o):
                    menace = o.menace
                    try:
                        self._enemy_menace[place] += menace
                    except:
                        self._enemy_menace[place] = menace
                        self._enemy_presence.append(place)
                    if o.range and o.range > PRECISION:
                        for place in place.neighbors:
                            try:
                                self._enemy_menace[place] += menace // 10
                            except:
                                self._enemy_menace[place] = menace // 10
                elif isinstance(o, Corpse):
                    self._places_with_corpses.add(place)
                elif o.player in self.allied and o.is_vulnerable:
                    self._places_with_friends.add(place)
                if o.time_limit and o.harm_level:
                    self._cataclysmic_places.add(place)

    def enemy_menace(self, place):
        try:
            return self._enemy_menace[place]
        except:
            return 0

    def is_very_dangerous(self, place_or_exit):
        if not self.is_dangerous(place_or_exit):
            # presence without menace
            return False
        try:
            return place_or_exit.other_side.place in self._enemy_presence
        except:
            return place_or_exit in self._enemy_presence

    def is_dangerous(self, place_or_exit):
        try:
            return place_or_exit.other_side.place in self._enemy_menace
        except:
            return place_or_exit in self._enemy_menace

    def balance(self, *squares):
        # The first square is where the fight will be.
        # TODO: take into account: versus air, ground
        # TODO: take into account: allies (in first square)
        a = 0
        for u in self.units:
            if u.place in squares:
                a += u.menace
        try:
            return a // self.enemy_menace(squares[0])
        except ZeroDivisionError:
            return 1000

    def _update_actual_speed(self):
        for u in self.units:
            try:
                if u.place.type_name in u.speed_on_terrain:
                    u.actual_speed = to_int(u.speed_on_terrain[u.speed_on_terrain.index(u.place.type_name) + 1])
                elif u.airground_type == "water":
                    u.actual_speed = u.speed
                else:
                    u.actual_speed = u.speed * u.place.terrain_speed[0 if u.airground_type == "ground" else 1] // 100
                if u.speed:
                    u.actual_speed = max(u.actual_speed , VERY_SLOW) # never stuck
            except:
                u.actual_speed = u.speed
        for g in list(self.groups.values()):
            if g:
                actual_speed = min(u.actual_speed for u in g)
                for u in g:
                    u.actual_speed = actual_speed

    def _update_drowning(self):
        for u in self.units[:]:
            if u.is_vulnerable and u.airground_type == "ground" \
               and not getattr(u.place, "is_ground", True):
                u.die()

    def update(self):
        self._update_actual_speed()
        self._update_storage_bonus()
        self._update_allied_upgrades()
        self._update_perception_and_memory()
        self._update_menace()
        self._update_enemy_menace_and_presence_and_corpses()
        self.play()
        self._update_drowning()

    def level(self, type_name):
        return self.upgrades.count(type_name)

    def has(self, type_name):
        if type_name in self.upgrades:
            return True
        for u in self.units:
            if u.type_name == type_name or type_name in u.expanded_is_a:
                return True
        return False

    def has_all(self, type_names):
        for t in type_names:
            if not self.has(t):
                return False
        return True

    def get_object_by_id(self, i):
        if isinstance(i, str) and i.startswith("zoom"):
            return ZoomTarget(i, self)
        if i in self.world.grid:
            return self.world.grid[i]
        if i in self.world.objects:
            o = self.world.objects[i]
            if o in self.world.squares or o in self.perception:
                return o
        for o in self.memory:
            if o.id == i:
                return o
        
    def is_local_human(self):
        return hasattr(self.client, "interface")

    def observe(self, o):
        # for example: a catapult firing from an unknown place
        # doesn't work for invisible units (hints are given in Starcraft though)
        if o.is_invisible or o.is_cloaked: return # don't observe dark archers
        self.observed_objects[o] = self.world.time + 3000

    def _memorize(self, o):
        if o in self._memory_index:
            self._memory_index[o].time_stamp = self.world.time
        else:
            remembrance = copy.copy(o)
            remembrance.time_stamp = self.world.time
            remembrance.initial_model = o
            self.memory.add(remembrance)
            self._memory_index[o] = remembrance

    def _forget(self, o): # o is a memory object
        self.memory.remove(o)
        try:
            del self._memory_index[o.initial_model]
        except KeyError: # a test requires this to pass
            pass
        o.place = None # make sure this object is not reused

    def remembers(self, actual_object):
        for remembrance in self.memory:
            if remembrance.initial_model is actual_object:
                return True

    def send_event(self, o, e):
        if self.is_local_human():
            self.client.push("event", copy.copy(o), e)

    def pay(self, cost):
        for i, c in enumerate(cost):
            self.resources[i] -= c

    def unpay(self, cost):
        self.pay([-c for c in cost])

    def _reserve_resources(self, project):
        self.pay(project.cost)
        self.budget.append(project)

    def resources_are_reserved(self, project):
        return project in self.budget

    def reserve_resources_if_needed(self, project):
        if not self.resources_are_reserved(project):
            self._reserve_resources(project)

    def free_resources(self, project):
        if project in self.budget:
            self.unpay(project.cost)
            self.budget.remove(project)

    def _no_worker_on_project(self, project):
        for u in self.units:
            if u.must_build(project):
                return False
        return True

    def free_project_resources_if_no_worker_on_project(self):
        for project in self.budget:
            if self._no_worker_on_project(project):
                self.free_resources(project)

    def send_alert(self, square, sound):
        self.push("alert", square.id, sound)

    def play(self):
        pass # play() is defined for computers

    def has_quit(self):
        return self not in self.world.players

    def quit_game(self):
        self.push("quit")
        if self in self.world.true_players():
            self.broadcast_to_others_only(self.name + mp.HAS_JUST_QUIT_GAME)
        for u in self.units[:]:
            u.delete()
        self.world.players.remove(self)
        self.world.ex_players.append(self)

    def clean(self):
        self.client.player = None
        self.__dict__ = {}

    is_human = False

    def push(self, *args):
        if self.client:
            self.client.push(*args)

    def execute_command(self, data):
        args = data.split()
        cmd = "cmd_" + args[0].lower()
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning(f"unknown command: '{cmd}' ({data})")

    def send_voice_important(self, msg):
        self.push("voice_important", encode_msg(msg))

    nb_units_produced = 0
    nb_units_lost = 0
    nb_units_killed = 0
    nb_buildings_produced = 0
    nb_buildings_lost = 0
    nb_buildings_killed = 0

    def equivalent(self, tn):
        if rules.get(self.faction, tn):
            return rules.get(self.faction, tn)[0]
        return tn

    def init_alliance(self):
        if self.client.alliance in [None, "None"]: return
        for p in self.world.players:
            if self.client.alliance == p.client.alliance:
                self.allied.append(p)

    def init_position(self):

        def equivalent_type(t):
            tn = getattr(t, "type_name", "")
            if rules.get(self.faction, tn):
                return self.world.unit_class(rules.get(self.faction, tn)[0])
            return t

        self.resources = self.start[0][:]
        normalize_cost_or_resources(self.resources)
        self.gathered_resources = self.resources[:]
        for place, type_ in self.start[1]:
            if self.world.must_apply_equivalent_type:
                type_ = equivalent_type(type_)
            if isinstance(type_, str) and type_[0:1] == "-":
                self.forbidden_techs.append(type_[1:])
            elif isinstance(type_, Upgrade):
                self.upgrades.append(type_.type_name) # type_.upgrade_player(self) would require the units already there
            elif not type_:
                warning("couldn't create an initial unit")
            else:
                place = self.world.grid[place]
                x, y, land = place.find_and_remove_meadow(type_)
                x, y = place.find_free_space(type_.airground_type, x, y)
                if x is not None:
                    unit = type_(self, place, x, y)
                    unit.building_land = land
                        
        self.triggers = self.start[2]

        if rules.get(self.faction, getattr(self, "AI_type", "")):
            self.set_ai(rules.get(self.faction, self.AI_type)[0])

    def store(self, _type, qty):
        qty += self.storage_bonus[_type]
        self.resources[_type] += qty
        self.gathered_resources[_type] += qty

    def run_triggers(self):
        if not self.is_playing:
            return
        for t in self.triggers[:]:
            condition, action = t
            if self.my_eval(condition):
                self.my_eval(action)
                if not self.is_playing: # after victory or defeat
                    break
                else:
                    self.triggers.remove(t)

    def my_eval(self, l):
        if hasattr(self, "lang_" + l[0]):
            return getattr(self, "lang_" + l[0])(l[1:])
        return False

    def lang_timer(self, args):
        # float(args[0]) is probably not a problem for synchro since the result
        # of the multiplication is not reused after the comparison.
        # And for example: 6 == .1 * 60 (tested in Python 2.4)
        return self.world.time // 1000 >= float(args[0]) * self.world.timer_coefficient
        
    def lang_order(self, args):
        select, orders = args
        for x in select:
            if x in self.world.grid:
                default_square = x
                multiplicator = 1
            elif re.match("[0-9]+$", x):
                multiplicator = int(x)
            else:
                for o in self.world.grid[default_square].objects:
                    if self.check_type(o, x) and (o.player == self):
                        for order in orders:
                            o.take_order(order, forget_previous=False)
                        multiplicator -= 1
                        if multiplicator == 0:
                            multiplicator = 1
                            break

    def lang_has(self, args):
        nb = 1
        for x in args:
            if re.match("[0-9]+$", x):
                nb = int(x)
            else:
                for u in self.units:
                    if self.check_type(u, x):
                        nb -= 1
                        if not nb:
                            break
                if nb:
                    return False
                nb = 1
        return True

    def lang_has_entered(self, args):
        player = self.world.players[0]
        for x in args:
            for o in self.world.grid[x].objects:
                if o in player.units and o.presence:
                    return True

    def _nb_scouts(self, square):
        n = 0
        for u in self.units:
            if u.place == square:
                n += 1
        return n

    def lang_add_units(self, items, target=None, decay=0, from_corpse=False, corpses=[], notify=True):
        sq = self.world.grid["a1"]
        multiplicator = 1
        for i in items:
            if i in self.world.grid:
                sq = self.world.grid[i]
                multiplicator = 1
            elif re.match("[0-9]+$", i):
                multiplicator = int(i)
            else:
                cls = self.world.unit_class(i)
                for _ in range(multiplicator):
                    if not self.check_count_limit(i):
                        break
                    land = None
                    if from_corpse:
                        if corpses:
                            corpse = corpses.pop(0)
                            x, y = corpse.x, corpse.y
                            sq = corpse.place
                            corpse.delete()
                        else:
                            return
                    elif target:
                        x, y = target.x, target.y 
                        sq = target if target in self.world.squares else target.place
                    else:
                        x, y, land = sq.find_and_remove_meadow(cls)
                    try:
                        u = cls(self, sq, x, y)
                        u.building_land = land
                    except NotEnoughSpaceError:
                        break
                    except:
                        warning("pb with lang_add_unit(%s, %s)", items, target)
                    if decay:
                        u.time_limit = self.world.time + decay
                    if notify:
                        u.notify("added")
                multiplicator = 1
            
    def lang_no_enemy_left(self, unused_args):
        return not [p for p in self.world.players if self.player_is_an_enemy(p)
                    and p.is_playing]

    def lang_no_enemy_player_left(self, unused_args):
        return not [p for p in self.world.true_players() if self.player_is_an_enemy(p)
                    and p.is_playing]

    def lang_no_unit_left(self, unused_args):
        return not self.units

    def lang_no_building_left(self, unused_args):
        for u in self.units:
            if u.provides_survival:
                return False
        return True

    def consumed_resources(self):
        return [self.gathered_resources[i] - self.resources[i] for i, c in enumerate(self.resources)]

    def _get_score(self):
        score = self.nb_units_produced - self.nb_units_lost + self.nb_units_killed + self.nb_buildings_produced - self.nb_buildings_lost + self.nb_buildings_killed
        for i, _ in enumerate(self.resources):
            score += (self.gathered_resources[i] + self.consumed_resources()[i]) // PRECISION
        return score

    def _get_score_msgs(self):
        if self.has_victory:
            victory_or_defeat = mp.VICTORY
        else:
            victory_or_defeat = mp.DEFEAT
        t = self.world.time // 1000
        m = int(t // 60)
        s = int(t - m * 60)
        msgs = []
        msgs.append(victory_or_defeat + mp.AT
                    + nb2msg(m) + mp.MINUTES
                    + nb2msg(s) + mp.SECONDS)
        msgs.append(nb2msg(self.nb_units_produced) + mp.UNITS + mp.PRODUCED_F
                    + mp.COMMA
                    + nb2msg(self.nb_units_lost) + mp.LOST
                    + mp.COMMA
                    + nb2msg(self.nb_units_killed) + mp.NEUTRALIZED)
        msgs.append(nb2msg(self.nb_buildings_produced) + mp.BUILDINGS + mp.PRODUCED_M
                    + mp.COMMA
                    + nb2msg(self.nb_buildings_lost) + mp.LOST
                    + mp.COMMA
                    + nb2msg(self.nb_buildings_killed) + mp.NEUTRALIZED)
        res_msg = []
        for i, _ in enumerate(self.resources):
            res_msg += nb2msg(self.gathered_resources[i] // PRECISION) \
                       + style.get("parameters", "resource_%s_title" % i) \
                       + mp.GATHERED + mp.COMMA \
                       + nb2msg(self.consumed_resources()[i] // PRECISION) \
                       + mp.CONSUMED + mp.PERIOD
        msgs.append(res_msg[:-1])
        msgs.append(mp.SCORE + nb2msg(self._get_score())
                    + mp.HISTORY_EXPLANATION)
        return msgs

    score_msgs = ()
    
    def store_score(self):
        self.score_msgs = self._get_score_msgs()

    def victory(self):
        for p in self.world.players:
            if p.is_playing:
                if p in self.allied_victory:
                    p.has_victory = True
                    p.store_score()
                else:
                    p.defeat()

    def defeat(self, force_quit=False):
        self.has_been_defeated = True
        self.store_score()
        if self in self.world.true_players():
            self.broadcast_to_others_only(self.name + mp.HAS_BEEN_DEFEATED)
        for u in self.units[:]:
            u.delete()
        if force_quit:
            self.quit_game()
        elif self.observer_if_defeated and self.world.true_playing_players:
            the_game_will_probably_continue = False
            allied_victory = self.world.true_playing_players[0].allied_victory
            for p in self.world.true_playing_players:
                if p not in allied_victory:
                    the_game_will_probably_continue = True
                    break
            if the_game_will_probably_continue:
                self.send_voice_important(mp.YOU_HAVE_BEEN_DEFEATED
                                          + mp.YOU_ARE_NOW_IN_OBSERVER_MODE)
            else:
                self.send_voice_important(mp.YOU_HAVE_BEEN_DEFEATED)
        else:
            self.quit_game()

    def lang_victory(self, unused_args):
        self.victory()

    def lang_defeat(self, unused_args):
        self.defeat()

    def lang_cut_scene(self, args):
        self.push("sequence", args)

    def lang_add_objective(self, args):
        n = args[0]
        o = Objective(n, [int(x) for x in args[1:]])
        if n not in self.objectives:
            self.objectives[n] = o
            self.send_voice_important(mp.NEW_OBJECTIVE + o.description)

    def lang_objective_complete(self, args):
        n = args[0]
        if n in self.objectives:
            self.send_voice_important(mp.OBJECTIVE_COMPLETE
                                      + self.objectives[n].description)
            del self.objectives[n]
            if self.objectives == {}:
                self.send_voice_important(mp.MISSION_COMPLETE)
                self.victory()

    def lang_ai(self, args):
        self.set_ai(args[0])

    def lang_faction(self, args):
        if args and args[0] in self.world.factions:
            self.faction = args[0]
        else:
            warning("unknown faction: %s", " ".join(args))

    @property
    def available_food(self):
        return min(self.food, self.world.food_limit)

    def on_unit_attacked(self, unit, attacker):
        pass

    def player_is_an_enemy(self, p):
        return p not in self.allied

    def is_an_enemy(self, o):
        return o.player is not None and o.player not in self.allied

    def broadcast_to_others_only(self, msg):
        for p in self.world.players:
            if p is not self:
                p.send_voice_important(msg)

    def check_type(self, o, t): # move method to Entity.check_type(t)?
        if isinstance(t, list):
            for _ in t:
                if self.check_type(o, _):
                    return True
        elif inspect.isclass(t): # Deposit, BuildingSite, Worker, Meadow...
            return isinstance(o, t)
        elif hasattr(t, "type_name"):
            return o.type_name == t.type_name
        elif isinstance(t, str):
            return o.type_name == t

    def future_count(self, type_name):
        result = 0
        for u in self.units:
            if u.type_name == type_name or \
                u.type_name == "buildingsite" and u.type.type_name == type_name: 
                result += 1
            for o in u.orders:
                # don't count the "build" orders because they might concern the same building
                if o.keyword in ("train", "upgrade_to") and o.type.type_name == type_name:
                    result += 1
        return result

    def check_count_limit(self, type_name):
        t = self.world.unit_class(type_name)
        if t is None:
            info("couldn't check count_limit for %r", type_name)
            return False
        if t.count_limit == 0:
            return True
        if self.future_count(t.type_name) >= t.count_limit:
            return False
        return True

    def nearest_warehouse(self, place, resource_type, include_building_sites=False):
        warehouses = []
        for p in self.allied:
            for u in p.units:
                if (resource_type in u.storable_resource_types
                    or include_building_sites
                       and isinstance(u, BuildingSite)
                       and resource_type in u.type.storable_resource_types):
                    d = place.shortest_path_distance_to(u.place, self)
                    if d == 0:
                        return u
                    if d is not None:
                        warehouses.append(((d, u.id), u)) # is u.id useful?
        warehouses.sort()
        if warehouses:
            return warehouses[0][1]
        else:
            return None

    def cmd_toggle_cheatmode(self, unused_args=None):
        if self.cheatmode:
            self.cheatmode = False
        else:
            self.cheatmode = True

    def cmd_cmd(self, args):
        self.my_eval(args)

    def _is_admin(self):
        return self.world.players.index(self) == 0

    def cmd_speed(self, args):
        if self._is_admin():
            for p in self.world.players:
                p.push("speed", float(args[0]))
        else:
            warning("non admin client tried to change game speed")

    def cmd_quit(self, unused_args):
        self.defeat(force_quit=True)

    @property
    def allied_control_units(self):
        result = []
        for p in self.allied_control:
            result.extend(p.units)
        return result

    def cmd_neutral_quit(self, unused_args):
        if self in self.world.players:
            self.quit_game()

    # Computer may use the following methods later

    def _reset_group(self, name):
        if name in self.groups:
            for u in self.groups[name]:
                u.group = None
            self.groups[name] = []

    def cmd_order(self, args):
        self.group_had_enough_mana = False
        try:
            order_id = self.world.get_next_order_id() # used when several workers must create the same construction site
            forget_previous = args[0] == "0"
            del args[0]
            imperative = args[0] == "1"
            del args[0]
            if args[0] == "reset_group":
                self._reset_group(args[1])
                return
            for u in self.group:
                if u.group and u.group != self.group:
                    if u in u.group: u.group.remove(u)
                    u.group = None
                if u.player in self.allied_control: # in case the unit has died or has been converted
                    try:
                        if args[0] == "default":
                            u.take_default_order(args[1], forget_previous, imperative, order_id)
                        else:
                            u.take_order(args, forget_previous, imperative, order_id)
                    except:
                        exception("problem with order: %s" % args)
        except:
            exception("problem with order: %s" % args)

    def cmd_control(self, args):
        self.group = []
        for obj_id in group.decode(" ".join(args)):
            for u in self.allied_control_units:
                if u.id == obj_id:
                    self.group.append(u)
                    break

    def cmd_say(self, args):
        msg = self.name + mp.SAYS + [" ".join(args)]
        self.broadcast_to_others_only(msg)
