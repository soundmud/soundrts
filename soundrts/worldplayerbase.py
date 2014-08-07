import copy
import inspect
import re
import string
import sys
import time

import config
from constants import *
import group
from lib.log import *
from msgs import encode_msg
import stats
import worldrandom
from worldunit import *
from worldupgrade import Upgrade


class Objective(object):

    def __init__(self, number, description):
        self.number = number
        self.description = description


def normalize_cost_or_resources(lst):
    n = int(rules.get("parameters", "nb_of_resource_types")[0])
    while len(lst) < n:
        lst += [0]
    while len(lst) > n:
        del lst[-1]


class Player(object):

    cheatmode = False
    name = None
    used_food = 0
    food = 0
    neutral = False
    observer_if_defeated = False
    has_victory = False
    has_been_defeated = False
    race = "human_race"

    group = ()
    group_had_enough_mana = False # used to warn if not enough mana

    def __init__(self, world, client):
        self.allied = [self]
        if self.name != "npc_ai":
            self.number = world.get_next_player_number()
        else:
            self.number = None
        self.perception = set()
        self.memory = set()
        self.id = world.get_next_id()
        self.world = world
        self.client = client
        self.ready = False # ignored if self.client.is_always_ready
        self.ia_start_index = 0
        self.ia_index = 0
        self.send_voice_important(self.world.introduction)
        self.objectives = {}
        self.units = []
        self.budget = []
        self.upgrades = []
        self.forbidden_techs = []
        self.places_to_explore = []
        self.observed_before_squares = []
        self.observed_squares = {}
        self.detected_squares = {}
        self.cloaked_squares = {}
        self.allied_control = (self, )
        self._known_enemies = {}
        self._known_enemies_time = {}
        self._enemy_menace = {}
        self._enemy_menace_time = {}
        self.enemy_doors = set()
        self._affected_squares = []

    @property
    def is_playing(self):
        return not (self.has_victory or self.has_been_defeated)

    def react_arrives(self, someone, door=None):
        if door is not None:
            self.enemy_doors.add(door)

    def known_enemies(self, place):
        # assert: "memory is not included"
        # warning: memory objects are not in place.objects
        if self._known_enemies_time.get(place) != self.world.time:
            enemy_units = []
            for e in self.world.players:
                if e.is_an_enemy(self):
                    enemy_units.extend(e.units)
            self._known_enemies[place] = [u for u in
                set(self.perception).intersection(enemy_units).intersection(place.objects)
                if u.is_vulnerable and not u.is_inside]
            self._known_enemies_time[place] = self.world.time
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

    def update(self):
        self._update_storage_bonus()
        self._update_allied_upgrades()
        self.play()

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

    def is_perceiving(self, o):
        if o is None or o.is_inside or o.place is None:
            return False
        for p in self.allied_vision:
            if o.player is p or (
            o.place in p.observed_squares and (
                not o.is_invisible_or_cloaked() or
                o.place in p.detected_squares)):
                return True
        return False

    def observe(self, o):
        # for example: a catapult firing from an unknown place
        # doesn't work for invisible units (hints are given in Starcraft though)
        if o.is_invisible_or_cloaked(): return # don't observe dark archers
        if not self.is_perceiving(o):
            self._remember(o)

    def _update_dict(self, dct, squares, inc):
        for square in squares:
            if square not in dct:
                dct[square] = 0
                self._affected_squares.append(square)
            dct[square] += inc
            if dct[square] == 0:
                del dct[square]
                self._affected_squares.append(square)
            else:
                assert dct[square] > 0

    def update_perception_of_object(self, o):
        if self.is_perceiving(o):
            if o not in self.perception:
                # add to perception
                self.perception.add(o)
                for m in list(self.memory):
                    if m.initial_model is o:
                        # forget it because you are perceiving it again
                        self._forget(m)
        elif o in self.perception:
            # remove from perception
            self.perception.remove(o)
            if o.player is not self and o.place is not None:
                self._remember(o)

    def _update_all_dicts(self, unit, inc):
        self._affected_squares = []
        self._update_dict(self.observed_squares, unit.get_observed_squares(), inc)
        if inc > 0:
            for square in unit.get_observed_squares():
                if square not in self.observed_before_squares:
                    self.observed_before_squares.append(square)
        if unit.is_a_detector:
            self._update_dict(self.detected_squares, [unit.place], inc)
        if unit.is_a_cloaker: # XXX allied vision != allied cloaking
            self._update_dict(self.cloaked_squares, [unit.place], inc)

    def update_all_dicts(self, unit, inc):
        if unit.place is None: return
        for p in self.allied_vision:
            p._update_all_dicts(unit, inc)
#        for p in self.allied_vision: # XXX (optimized but incorrect for cloaker)
        for p in self.world.players: # necessary for cloaker (XXX not optimized though)
            for square in self._affected_squares:
                for o in square.objects:
                    p.update_perception_of_object(o)
                if square in p.observed_squares:
                    # forget what is remembered there
                    for m in list(p.memory):
                        if m.place is square:
                            p._forget(m)

    def _remember(self, o):
        for m in self.memory:
            if m.initial_model is o:
                self.memory.remove(m)
                break
        remembrance = copy.copy(o)
        remembrance.time_stamp = self.world.time
        remembrance.initial_model = o
        self.memory.add(remembrance)

    def _forget(self, o):
        self.memory.remove(o)
        o.place = None # make sure this object is not reused

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
        debug("quit_game %s", self.name)
        self.push("quit")
        if self in self.world.true_players():
            self.broadcast_to_others_only([self.name, 4261])
        for u in self.units[:]:
            u.delete()
        self.world.players.remove(self)
        self.world.ex_players.append(self)
#        self.update_eventuel()

    def clean(self):
        self.client.player = None
        self.__dict__ = {}

    def is_human(self):
        return False

    def push(self, *args):
        if self.client:
            self.client.push(*args)

    def execute_command(self, data):
        args = string.split(data)
        cmd = "cmd_" + string.lower(args[0])
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning("unknown command: '%s' (%s)" % (cmd, data))

    def send_voice_important(self, msg):
        self.push("voice_important", encode_msg(msg))

    def update_eventuel(self):
        for p in self.world.players:
            if p.is_human() and not p.ready:
                debug("no update yet: %s is not ready", p.client.login)
                return # not yet
        self.world.update()

    nb_units_produced = 0
    nb_units_lost = 0
    nb_units_killed = 0
    nb_buildings_produced = 0
    nb_buildings_lost = 0
    nb_buildings_killed = 0

    def equivalent(self, tn):
        if rules.get(self.race, tn):
            return rules.get(self.race, tn)[0]
        return tn
        
    def init_position(self):

        def equivalent_type(t):
            tn = getattr(t, "type_name", "")
            if rules.get(self.race, tn):
                return self.world.unit_class(rules.get(self.race, tn)[0])
            return t

        self.resources = self.start[0][:]
        normalize_cost_or_resources(self.resources)
        self.gathered_resources = self.resources[:]
        for place, type_ in self.start[1]:
            type_ = equivalent_type(type_)
            if isinstance(type_, str) and type_[0:1] == "-":
                self.forbidden_techs.append(type_[1:])
            elif isinstance(type_, Upgrade):
                self.upgrades.append(type_.type_name) # XXX type_.upgrade_player(self)?
            else:
                place = self.world.grid[place]
                x, y = place.find_and_remove_meadow(type_)
                x, y = place.find_free_space(type_.airground_type, x, y)
                if x is not None:
                    type_(self, place, x, y)
        self.triggers = self.start[2]

        if rules.get(self.race, getattr(self, "AI_type", "")):
            self.set_ai(rules.get(self.race, self.AI_type)[0])

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
        return self.world.time / 1000 >= float(args[0]) * self.world.timer_coefficient
        
    def lang_order(self, args):
        select, orders = args
        for x in select:
            if self.world.grid.has_key(x):
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
        for x in args:
            for o in self.world.grid[x].objects:
                if o in self.units and o.presence:
                    return True

    def _nb_scouts(self, square):
        n = 0
        for u in self.units:
            if u.place == square:
                n += 1
        return n

    def lang_add_units(self, items, decay=0, from_corpse=False, notify=True):
        for x in items:
            if self.world.grid.has_key(x):
                sq = self.world.grid[x]
                multiplicator = 1
            elif re.match("[0-9]+$", x):
                multiplicator = int(x)
            else:
                cls = self.world.unit_class(x)
                for _ in range(multiplicator):
                    if from_corpse:
                        corpse = None
                        for o in sq.objects:
                            if isinstance(o, Corpse):
                                corpse = o
                                break
                        if corpse is not None:
                            x, y = corpse.x, corpse.y
                            corpse.delete()
                        else:
                            return
                    else:
                        x, y = sq.find_and_remove_meadow(cls)
                    try:
                        u = cls(self, sq, x, y)
                    except NotEnoughSpaceError:
                        break
                    if decay:
                        u.time_limit = self.world.time + decay
                    if notify:
                        u.notify("added")
                multiplicator = 1
            
    def lang_no_enemy_left(self, unused_args):
        return not [p for p in self.world.players if self.is_an_enemy(p)
                    and p.is_playing]

    def lang_no_enemy_player_left(self, unused_args):
        return not [p for p in self.world.true_players() if self.is_an_enemy(p)
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
            score += (self.gathered_resources[i] + self.consumed_resources()[i]) / PRECISION
        return score

    def _get_score_msgs(self):
        if self.has_victory:
            victory_or_defeat = [149]
        else:
            victory_or_defeat = [150]
        t = self.world.time / 1000
        m = int(t / 60)
        s = int(t - m * 60)
        msgs = []
        msgs.append(victory_or_defeat + [107] + nb2msg(m) + [65]
                    + nb2msg(s) + [66]) # in ... minutes and ... seconds
        msgs.append(nb2msg(self.nb_units_produced) + [130, 4023, 9998]
                    + nb2msg(self.nb_units_lost) + [146, 9998]
                    + nb2msg(self.nb_units_killed) + [145])
        msgs.append(nb2msg(self.nb_buildings_produced) + [4025, 4022, 9998]
                    + nb2msg(self.nb_buildings_lost) + [146, 9998]
                    + nb2msg(self.nb_buildings_killed) + [145])
        res_msg = []
        for i, _ in enumerate(self.resources):
            res_msg += nb2msg(self.gathered_resources[i] / PRECISION) \
                       + style.get("parameters", "resource_%s_title" % i) \
                       + [4256, 9998] \
                       + nb2msg(self.consumed_resources()[i] / PRECISION) \
                       + [4024, 9999]
        msgs.append(res_msg[:-1])
        msgs.append([4026] + nb2msg(self._get_score()) + [2008])
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
            self.broadcast_to_others_only([self.name, 4311]) # "defeated"
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
                self.send_voice_important([4312, 4313]) # "defeated" "observer mode"
            else:
                self.send_voice_important([4312]) # "defeated"
            if not self.cheatmode:
                self.cmd_toggle_cheatmode()
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
        if not self.objectives.has_key(n):
            self.objectives[n] = o
            self.send_voice_important([4268] + o.description) # "new objective"

    def lang_objective_complete(self, args):
        n = args[0]
        if self.objectives.has_key(n):
            self.send_voice_important([4269] + self.objectives[n].description)
            del self.objectives[n]
            if self.objectives == {}:
                self.send_voice_important([4270])
                self.victory()

    def lang_ai(self, args):
        self.set_ai(args[0])

    def lang_race(self, args):
        if args and args[0] in self.world.get_races():
            self.race = args[0]
        else:
            warning("unknown race: %s", " ".join(args))

    @property
    def available_food(self):
        return min(self.food, self.world.food_limit)

    def on_resource_exhausted(self):
        pass

    def on_unit_flee(self, unit):
        pass

    def is_an_enemy(self, object):
        if isinstance(object, Player):
            return object not in self.allied
        elif hasattr(object, "player"):
            return self.is_an_enemy(object.player)
        else:
            return False

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
        
    def nb(self, types):
        n = 0
        for u in self.units:
            if self.check_type(u, types):
                n += 1
        return n

    def nearest_warehouse(self, place, resource_type):
        warehouses = []
        for p in self.allied:
            for u in p.units:
                if resource_type in u.storable_resource_types:
                    d = place.shortest_path_distance_to(u.place)
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
            self._update_dict(self.observed_squares, self.world.squares, -1)
            self._update_dict(self.detected_squares, self.world.squares, -1)
            for sq in self.world.squares:
                for o in sq.objects:
                    o.update_perception()
            # assertion:
            # observed_before_squares is not affected by _update_dict
            # (only update_all_dicts() would do that)
            for o in list(self.memory):
                if o.place not in self.observed_before_squares:
                    self.memory.remove(o)
        else:
            self.cheatmode = True
            self._update_dict(self.observed_squares, self.world.squares, 1)
            self._update_dict(self.detected_squares, self.world.squares, 1)
            for sq in self.world.squares:
                for o in sq.objects:
                    o.update_perception()

    def _is_admin(self):
        return self.client == self.world.admin

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
