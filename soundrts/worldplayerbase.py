import copy
import inspect
import re
import string

from constants import MAX_NB_OF_RESOURCE_TYPES
from definitions import rules, style
from lib.log import debug, warning
from lib.msgs import encode_msg, nb2msg
from lib.nofloat import PRECISION
import msgparts as mp
from worldentity import NotEnoughSpaceError, Entity
from worldresource import Corpse
from worldunit import BuildingSite, Soldier
from worldupgrade import Upgrade


class ZoomTarget(object):

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
        # TODO: improve this when ZoomTarget is replaced
        # with Subsquare and there is 1 building land or resource
        # in each subsquare. 
        return self.place.building_land # XXX imprecise

    def contains(self, x, y):
        subsquare = self.place.world.get_subsquare_id_from_xy
        return subsquare(self.x, self.y) == subsquare(x, y)


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
    faction = "human_faction"
    memory_duration = 30000 # 30 seconds of world time

    group = ()
    group_had_enough_mana = False # used to warn if not enough mana

    smart_units = False

    groups = {}

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
        x = place.x * 3 / self.world.square_width
        y = place.y * 3 / self.world.square_width
        candidates = list((x + dx, y + dy) for dx in (0, 1, -1) for dy in (0, 1, -1))
        sub = sorted(candidates, key=self._get_threat)[0]
        return (sub[0] * self.world.square_width / 3 + self.world.square_width / 6,
                sub[1] * self.world.square_width / 3 + self.world.square_width / 6)
    
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

    def _update_perception(self): # XXX for each allied_vision?
        if self.cheatmode:
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
            for u in p.units:
                self.observed_squares.update(u.get_observed_squares(strict=True))
                partially_observed_squares.update(u.get_observed_squares())
        partially_observed_squares -= self.observed_squares
        for s in self.observed_squares:
            for o in s.objects:
                if o.player is None:
                    self.perception.add(o)
        # partially observed squares show the terrain as memory with a fog of war warning
        for s in partially_observed_squares:
            for o in s.objects:
                if o.player is None:
                    self._memorize(o)
        self.observed_before_squares.update(partially_observed_squares)
        # objects revealed by their actions
        for p in self.allied_vision:
            # XXX cleaning should be done by each player
            for o in p.observed_objects.keys():
                # remove old observed objects and deleted objects
                if (p.observed_objects[o] < self.world.time
                    or o.place is None):
                    del p.observed_objects[o]
            # XXX this can be shared
            p.perception.update(p.observed_objects.keys())
        # sight
        for p in self.world.players:
            if p in self.allied_vision:
                self.perception.update(p.units)
            else:
                for u in p.units:
                    if (u.is_invisible or u.is_cloaked) and u not in self.detected_units:
                        continue
                    for avp in self.allied_vision:
                        for avu in avp.units:
                            from lib.nofloat import square_of_distance
                            radius2 = avu.sight_range * avu.sight_range
                            # XXX add wall condition (get_observed_squares only if radius<10*PRECISION)
                            if (square_of_distance(avu.x, avu.y, u.x, u.y) < radius2
                                and (avu.sight_range >= self.world.square_width
                                     or u.place in avu.get_observed_squares())):
                                self.perception.add(u)
                                continue
        # remove units inside buildings from perception
        # XXX even friendly units?
        # remove deleted units from perception
        for o in self.perception.copy():
##            if o.place is None:
##                print "removed", o.id
##                self.perception.remove(o)
            if o.is_inside:
                self.perception.remove(o)

    def _update_memory(self, previous_perception):
        # XXX forget deleted corpses, burning buildings, etc, only when an observer notices the absence
        self.observed_before_squares.update(self.observed_squares)
        for m in self.memory.copy():
            # forget units reappearing elsewhere
            # forget deleted units XXX should be done only if memory is in sight range
            # forget old memories of mobile units
            if (m.initial_model in self.perception
                or m.initial_model.place is None
                or m.initial_model.speed and m.time_stamp + self.memory_duration < self.world.time):
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
            for o in l:
                if self.is_an_enemy(o):
                    menace = o.menace
                    try:
                        self._enemy_menace[o.place] += menace
                    except:
                        self._enemy_menace[o.place] = menace
                        self._enemy_presence.append(o.place)
                    if o.range > PRECISION:
                        for place in o.place.neighbours:
                            try:
                                self._enemy_menace[place] += menace / 10
                            except:
                                self._enemy_menace[place] = menace / 10
                elif isinstance(o, Corpse):
                    self._places_with_corpses.add(o.place)
                elif o.player in self.allied and o.is_vulnerable:
                    self._places_with_friends.add(o.place)
                if o.time_limit and o.harm_level:
                    self._cataclysmic_places.add(o.place)

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
        # the first square is where the fight will be
        # XXX versus air, ground
        # XXX allies (in first square)
        a = 0
        for u in self.units:
            if u.place in squares:
                a += u.menace
        try:
            return a / self.enemy_menace(squares[0])
        except ZeroDivisionError:
            return 1000

    def _update_actual_speed(self):
        for u in self.units:
            u.actual_speed = u.speed
        for g in self.groups.values():
            if g:
                actual_speed = min(u.speed for u in g)
                for u in g:
                    u.actual_speed = actual_speed

    def update(self):
        self._update_actual_speed()
        self._update_storage_bonus()
        self._update_allied_upgrades()
        self._update_perception_and_memory()
        self._update_menace()
        self._update_enemy_menace_and_presence_and_corpses()
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
        if rules.get(self.faction, tn):
            return rules.get(self.faction, tn)[0]
        return tn
        
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
            type_ = equivalent_type(type_)
            if isinstance(type_, str) and type_[0:1] == "-":
                self.forbidden_techs.append(type_[1:])
            elif isinstance(type_, Upgrade):
                self.upgrades.append(type_.type_name) # XXX type_.upgrade_player(self)?
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
        multiplicator = 1
        for i in items:
            if self.world.grid.has_key(i):
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
            score += (self.gathered_resources[i] + self.consumed_resources()[i]) / PRECISION
        return score

    def _get_score_msgs(self):
        if self.has_victory:
            victory_or_defeat = mp.VICTORY
        else:
            victory_or_defeat = mp.DEFEAT
        t = self.world.time / 1000
        m = int(t / 60)
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
            res_msg += nb2msg(self.gathered_resources[i] / PRECISION) \
                       + style.get("parameters", "resource_%s_title" % i) \
                       + mp.GATHERED + mp.COMMA \
                       + nb2msg(self.consumed_resources()[i] / PRECISION) \
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

    def _quit_alliance(self):
        for ally in self.allied:
            if ally is not self:
                ally.allied.remove(self)
        self.allied =[self]

    def defeat(self, force_quit=False):
        self.has_been_defeated = True
        self._quit_alliance()
        self.store_score()
        if self in self.world.true_players():
            self.broadcast_to_others_only([self.name] + mp.HAS_BEEN_DEFEATED)
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
            self.send_voice_important(mp.NEW_OBJECTIVE + o.description)

    def lang_objective_complete(self, args):
        n = args[0]
        if self.objectives.has_key(n):
            self.send_voice_important(mp.OBJECTIVE_COMPLETE
                                      + self.objectives[n].description)
            del self.objectives[n]
            if self.objectives == {}:
                self.send_voice_important(mp.MISSION_COMPLETE)
                self.victory()

    def lang_ai(self, args):
        self.set_ai(args[0])

    def lang_faction(self, args):
        if args and args[0] in self.world.get_factions():
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

    def cmd_neutral_quit(self, unused_args):
        if self in self.world.players:
            self.quit_game()
