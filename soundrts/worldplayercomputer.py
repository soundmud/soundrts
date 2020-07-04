import re

from .definitions import get_ai, rules
from .lib.log import info, warning, exception
from .version import IS_DEV_VERSION
from .worldplayerbase import Player
from .worldresource import Meadow, Deposit, Corpse
from .worldunit import Worker, BuildingSite, Soldier
from soundrts.lib.nofloat import PRECISION, square_of_distance
from soundrts.worldorders import UseOrder


def value_as_an_explorer(u):
    air = 1 if u.airground_type == "air" else 0
    return ((air, u.speed, u.hp), u.id)


class Computer(Player):

    AI_type = None
    # the AI might need a longer memory than the player
    memory_duration = 36000000 # 36000 seconds of world time
    _sensible_building = None

    def __init__(self, world, client):
        self._attacked_places = []
        self._orders = {}
        self._previous_choose = {}
        self.neutral = client.neutral
        Player.__init__(self, world, client)
        self.set_ai(client.AI_type)

    def __repr__(self):
        return "Computer(%s)" % self.client

    @property
    def is_cpu_intensive(self):
        return self.AI_type != "timers"

    @property
    def smart_units(self):
        return self.AI_type != "timers"

    def set_ai(self, ai):
        self.AI_type = ai
        if self.AI_type == "timers": return
        self._plan = get_ai(ai)
        # set or reset default values
        self._line_nb = 0
        self.watchdog = 0
        self.constant_attacks = 0
        self.research = 0
        self._update_effect_users_and_workers() # required by some tests

    _previous_linechange = 0
    __line_nb = 0
##    _prev_line_nb = None

    def get_line_nb(self):
        return self.__line_nb

    def set_line_nb(self, value):
        self.__line_nb = value
        self._previous_linechange = self.world.time

    _line_nb = property(get_line_nb, set_line_nb)

    def _follow_plan(self):
        if not self._plan: return
        if self.watchdog and self.world.time > \
           self._previous_linechange + self.watchdog * 1000:
            self._line_nb += 1
        self._line_nb %= len(self._plan)
        line = self._plan[self._line_nb]
        cmd = line.split()
        if cmd:
            if cmd[0] == "goto":
                if re.match("^[+-][0-9]+$", cmd[1]):
                    self._line_nb += int(cmd[1])
                elif "label " + cmd[1] in self._plan:
                    self._line_nb = self._plan.index("label " + cmd[1])
                elif re.match("^[0-9]+$", cmd[1]):
                    self._line_nb = int(cmd[1])
                else:
                    warning("goto: wrong destination: %s", cmd[1])
                    self._line_nb += 1
            elif cmd[0] == "label":
                self._line_nb += 1
                info(cmd[1])
            elif cmd[0] == "goto_random":
                dest = self.world.random.choice(cmd[1:])
                if "label " + dest in self._plan:
                    self._line_nb = self._plan.index("label " + dest)
                else:
                    warning("goto_random: label not found: %s", dest)
                    self._line_nb += 1
            elif cmd[0] == "attack":
                self.constant_attacks = 1
                self._line_nb += 1
            elif cmd[0] in ("watchdog", "constant_attacks",
                            "research"):
                setattr(self, cmd[0], int(cmd[1]))
                self._line_nb += 1
            elif cmd[0] == "get":
                n = 1
                done = True
                for w in cmd[1:]:
                    if re.match("^[0-9]+$", w):
                        n = int(w)
                    elif w in rules.classnames():
                        if not self.get(n, self.equivalent(w)):
                            done = False
                            break
                        n = 1
                    else:
                        warning("get: unknown unit: '%s' (in ai.txt)", w)
                        n = 1
                if done:
                    self._line_nb += 1
            else:
                warning("unknown command: '%s' (in ai.txt)", cmd[0])
                self._line_nb += 1

    def _best_warehouse(self, place=None):
        return self.world.unit_class(self.equivalent("townhall"))

    def _build_a_warehouse_for(self, deposit):
        def nearby_workers():
            return [v for v in self._workers if
                    (v.place is deposit.place
                     or v.orders and v.orders[0].keyword == "gather"
                        and (v.orders[0].target is None
                             or v.orders[0].target.place is deposit.place))]
        nearby_workers = nearby_workers()
        if not nearby_workers:
            return
        wh = self.nearest_warehouse(deposit.place, deposit.resource_type, include_building_sites=True)
        if isinstance(wh, BuildingSite):
            for v in nearby_workers:
                v.take_order(["repair", wh.id])
        elif (wh is None
            or deposit.place.shortest_path_distance_to(wh.place, self, avoid=True)
               > self.world.square_width):
            meadow = self.choose(Meadow, starting_place=deposit.place)
            if meadow:
                for v in nearby_workers:
                    v.take_order(["build", self._best_warehouse(deposit.place).type_name, meadow.id])

    def _build_a_warehouse_if_useful(self):
        if self.missing_resources(self._best_warehouse().cost):
            return
        for deposit in [o.target for u in self._workers for o in u.orders
                    if o.keyword == "gather" and o.target is not None and o.target.place is not None]:
            self._build_a_warehouse_for(deposit)

    def idle_buildings_research(self):
        for u in self.units:
            if not u.orders:
                for t in u.can_research:
                    if not self.future_nb([t]) \
                       and not self.missing_resources(self.unit_class(t).cost) \
                       and self.potential(self.unit_class(t).cost) > 3:
                        u.take_order(["research", t])

    def _is_powerful_enough(self, units, place):
        # sometimes food limit prevents units with more than 1 food cost
        ratio = 180 if self.used_food < self.world.food_limit - 5 else 100
        return sum(u.menace for u in units if u.speed > 0 and isinstance(u, Soldier)) > self.enemy_menace(place) * ratio // 100

    def _send_workers_to_forgotten_building_sites(self):
        for site in self._building_sites:
            if not [u for u in self._workers if u.orders and u.orders[0].target == site]:
                self.order(4, Worker, ["repair", site.id], requisition=True, near=site)
                break

    def _idle_workers_gather(self):
        idle = [u for u in self._workers if not u.orders]
        if idle:
            for u in idle:
                deposit = self.choose(Deposit, starting_place=u.place, random=True)
                if not deposit:
                    return
                u.take_order(["gather", deposit.id])
                try:
                    self._gathered_deposits[deposit] += 1
                except:
                    self._gathered_deposits[deposit] = 1

    def _should_play_this_turn(self):
        players = self.world.cpu_intensive_players()
        turn = players.index(self) * 10 // len(players)
        return self.world.turn % 10 == turn

    def _defensive_routine(self):
        if self._sensible_building is not None:
            if self._sensible_building not in self.units:
                self._sensible_building = None

        # regroup at a valuable place (and get healed or repaired)
        self._send_units(self._idle_fighters, self._builders_place())

        # commented-out variant: regroup at a dangerous place
        # if self._sensible_building is None:
        #     self._send_units(self._idle_fighters, self._builders_place())
        # else:
        #     wounded = [u for u in self._idle_fighters if u.hp < u.hp_max]
        #     ok = [u for u in self._idle_fighters if u.hp == u.hp_max]
        #     self._send_units(wounded, self._builders_place())
        #     self._send_units(ok, self._sensible_building.place)

        # build static defenses
        if self._sensible_building is not None:
            def nearest_exit(u):
                result = sorted(u.place.exits, key=lambda e: square_of_distance(u.x, u.y, e.x, e.y))
                if result:
                    return result[0]
            e = nearest_exit(self._sensible_building)
            if e is not None and not e.is_blocked() and self.gather(self.world.unit_class("gate").cost, 0):
                for w in self._workers:
                    w.take_order(["build", "gate", e.id])

    def play(self):
        if self.AI_type == "timers": return
        if not self._should_play_this_turn(): return
        #print self.number, "plays turn", self.world.turn
        self._update_effect_users_and_workers()
        self._update_time_has_come()
        self._send_workers_to_forgotten_building_sites()
        self._idle_workers_gather()
        self._send_explorer()
        if self._attacked_places:
            self._eventually_attack(self._attacked_places)
            self._attacked_places = []
        elif self.constant_attacks:
            self._eventually_attack(self._enemy_presence)
        else:
            self._defensive_routine()
        if self.research:
            self.idle_buildings_research()
        self._raise_dead()
        self._build_a_warehouse_if_useful()
        self.get(10, self.equivalent("peasant"))
        try:
            self._follow_plan()
        except RuntimeError:
            warning("recursion error with %s; current ai.txt line is: %s",
                    self.AI_type, self._plan[self._line_nb])
            if IS_DEV_VERSION:
                exception("")
            self._line_nb += 1 # go to next step

    def _deposit_priority(self, deposit):
        if deposit is None:
            return -100, 0, 0
        try:
            workers = self._gathered_deposits[deposit]
        except:
            workers = 0
        # The resources difference is taken into account only if the difference is significant.
        return -self.resources[deposit.resource_type] // 10, -workers, deposit.id # deterministic (avoid sync errors)

    def _update_effect_users_and_workers(self):
        self._workers = []
        self._gathered_deposits = {}
        self._building_sites = []
        self._raise_dead_users = []
        self._teleportation_users = []
        self._cataclysm_users = []
        self._detector_users = []
        self._summon_users = []
        for u in self.units:
            if isinstance(u, Worker):
                self._workers.append(u)
                if u.orders and u.orders[0].keyword == "gather":
                    try:
                        self._gathered_deposits[u.orders[0].target] += 1
                    except:
                        self._gathered_deposits[u.orders[0].target] = 1
            elif isinstance(u, BuildingSite):
                self._building_sites.append(u)
            for a in u.can_use:
                if not UseOrder.is_allowed(u, a):
                    continue
                e = rules.get(a, "effect")
                if not e:
                    continue
                elif e[0] == "raise_dead":
                    self._raise_dead_users.append((u, a))
                elif e[0] == "teleportation":
                    self._teleportation_users.append((u, a))
                elif e[0] == "summon":
                    for item in e[1:]:
                        if rules.get(item, "harm_level"):
                            self._cataclysm_users.append((u, a))
                        if rules.get(item, "is_a_detector"):
                            self._detector_users.append((u, a))
                        if rules.get(item, "damage"):
                            self._summon_users.append((u, a))

    def _raise_dead(self):
        for u, a in self._raise_dead_users:
            if u.place in self._places_with_corpses:
                u.take_order(["use", a, u.place.id]) # optional target will be eventually ignored

    def missing_resources(self, cost):
        result= []
        for i, c in enumerate(cost):
            if c > self.resources[i]:
                result.append(i)
        return result

    def unit_class(self, name):
        return self.world.unit_class(name)

    def best_explorers(self):
        return sorted([u for u in self.units if u.speed > 0
                       and not (u.orders and u.orders[0].keyword == "upgrade_to")],
                      key=value_as_an_explorer, reverse=True)

    def _send_explorer(self):
        candidates = self.best_explorers()
        if candidates:
            best_explorer = candidates[0]
            if not (best_explorer.orders
                    and best_explorer.orders[0].keyword == "auto_explore"):
                explorer = None
                for u in self.units:
                    if u.orders and u.orders[0].keyword == "auto_explore":
                        explorer = u
                        break 
                if explorer:
                    if value_as_an_explorer(explorer)[0] == value_as_an_explorer(best_explorer)[0]:
                        return
                    explorer.take_order(["go", self.units[0].place.id])
                best_explorer.take_order(["auto_explore"])

    def _remove_far_candidates(self, candidates, start, limit):
        ids = {o.id: o for o in candidates}
        c = []
        queue = [start]
        done = []
        while queue and len(c) < limit:
            room = queue.pop(0)
            for o in room.objects:
                if o.id in ids:
                    c.append(ids[o.id])
                    if len(c) >= limit:
                        break
            if room in done:
                continue
            for e in room.exits:
                next_room = e.other_side.place
                if next_room not in done:
                    queue.append(next_room)
            done.append(room)
        return c

    def is_ok_for_warehouse(self, z, resource_type):
        # Eventually, to completely avoid cheating, is_ok() would
        # return True if "no owned warehouse and no remembered enemy".
        # a warehouse (allied or not) must not be already there
        for o2 in z.objects:
            if resource_type in getattr(o2, "storable_resource_types", ()):
                return False
        # a resource must be there
        for o in z.objects:
            if isinstance(o, Deposit) and o.resource_type == resource_type:
                return True

    def choose(self, c, resource_type=None, starting_place=None, random=False):
        if not self.units:
            return
        def is_ok(o):
            return o.place is not None \
               and (resource_type is None or self.is_ok_for_warehouse(o.place, resource_type)) \
               and not self.square_is_dangerous(o.place)
        k = f"{c} {resource_type} {starting_place}"
        if k in self._previous_choose and not random:
            o = self._previous_choose[k]
            if (o in self.perception or o in self.memory) and is_ok(o):
#                warning("useful cache %s %s", c, resource_type)
                return o
            else:
                del self._previous_choose[k]
        if starting_place is None:
            starting_place = self.units[0].place
        candidates = [o for o in self.perception.union(self.memory)
                      if self.check_type(o, c) and is_ok(o)]
        candidates = sorted(candidates, key=lambda x: x.id) # avoid synchronization errors
        if len(candidates) > 10:
            candidates = self._remove_far_candidates(candidates, starting_place, 10)
        else:
            candidates.sort(key=lambda x: starting_place.shortest_path_distance_to(x.place, self, avoid=True))
            while candidates and starting_place.shortest_path_distance_to(candidates[-1].place, self, avoid=True) is float("inf"):
                del candidates[-1] # no path
        if random:
            if candidates:
                p = candidates[0].place
                candidates = sorted([o for o in candidates if o.place is p],
                                    key=self._deposit_priority, reverse=True)
        for o in candidates:
            if not random:
                self._previous_choose[k] = o
            return o

    def nb(self, types):
        if types and isinstance(types, list) and isinstance(types[0], str) and types[0] in self.upgrades:
            return 1
        n = 0
        for u in self.units:
            if self.check_type(u, types):
                n += 1
        return n

    def _nb_in_production(self, types):
        n = 0
        for u in self.units:
            if isinstance(u, BuildingSite) and self.check_type(u.type, types):
                n += 1
                continue
            for o in u.orders:
                if o.keyword in ("build", "train", "upgrade_to", "research") and self.check_type(o.type, types):
                    # the result might be temporarily too high because of build orders
                    # but that's not a big problem for order()
                    n += 1
        return n

    def future_nb(self, types):
        return self.nb(types) + self._nb_in_production(types)

    def _worker_orders_priority(self, u):
        if not u.orders:
            return (0, )
        if u.orders[0].keyword == "gather":
            return (1, self._deposit_priority(u.orders[0].target))
        return (2, )

    def order(self, nb, types, order, near=None, requisition=False):
        order_id = repr((types, order))
        if order_id in self._orders:
            for unit_order in list(self._orders[order_id]):
                if unit_order.is_complete:
                    self._orders[order_id].remove(unit_order)
                elif unit_order.unit.place is None or unit_order not in unit_order.unit.orders:
                    self._orders[order_id].remove(unit_order)
        else:
            self._orders[order_id] = []
        if len(self._orders[order_id]) >= nb:
            return
        units = [u for u in self.units if self.check_type(u, types)]
        while units:
            if requisition:
                units.sort(key=self._worker_orders_priority)
            u = units.pop(0)
            if order[0] == "upgrade_to" and u.orders and u.orders[0].keyword == "auto_explore":
                u.take_order(["stop"])
            if requisition or not u.orders:
                if u.orders and u.orders[0].keyword in ("build", "repair"):
                    continue
                if requisition and u.orders and u.orders[0].keyword == "gather":
                    self._gathered_deposits[u.orders[0].target] -= 1
                u.take_order(order)
                if u.orders and u.orders[0].keyword == order[0]:
                    self._orders[order_id].append(u.orders[0])
                    if len(self._orders[order_id]) >= nb:
                        return

    def potential(self, cost):
        result = 9999
        for i, res in enumerate(self.resources):
            if cost[i]:
                result = min(result, res // cost[i])
        return result

    def get(self, nb, type):
        self._safe_cnt = 0
        return self._get(nb, [type])

    def _get(self, nb, types):
        if isinstance(types, str):
            types = [types]
        if self.nb(types) >= nb:
            return True
        if self.future_nb(types) >= nb:
            return False
        self._safe_cnt += 1
        if self._safe_cnt > 10:
            info("AI has trouble getting: %s %s", nb, types)
            return False
        for type in types:
            if type.__class__ == str:
                type = self.world.unit_class(type)
            if type is None:
                continue
            makers = self.world.get_makers(type)
            if self.nb(makers) > 0:
                self.build_or_train_or_upgradeto_or_summon(type, nb - self.future_nb(types))
                break
            elif makers:
                self._get(1, makers[0])
                return False
        return False

    def gather(self, cost, food):
        if self.missing_resources(cost):
            return
        if food != 0 and food > self.food - self.used_food:
            t = self.equivalent("farm")
            if self.future_nb(t) == self.nb(t):
                self.build_or_train_or_upgradeto_or_summon(t)
        else:
            return True

    def _get_requirements(self, t):
        for r in t.requirements:
            if not self.has(r): # requirement (eventually is_a)
                return self._get(1, r) # exact type
        return True

    def _builders_place(self):
        starts = {}
        for u in self._workers:
            if u.place not in starts: starts[u.place] = 1
            else: starts[u.place] += 1
        if starts:
            return sorted(list(starts.items()), key=lambda x: (x[1], x[0].id))[-1][0]

    def build_or_train_or_upgradeto_or_summon(self, t, nb=1):
        if t.__class__ == str:
            t = self.world.unit_class(t)
        type = t.__name__
        makers = self.world.get_makers(type)
        if self._get(1, makers) and self._get_requirements(t):
            for maker in makers:
                # TODO: choose one without orders if possible
                if self.nb(maker):
                    break
            if type in self.world.unit_class(maker).can_upgrade_to:
                if self.nb(maker) >= nb:
                    m = self.world.unit_class(maker)
                    if self.gather([t.cost[i] - m.cost[i] for i in range(len(t.cost))],
                                   t.food_cost - m.food_cost):
                        self.order(nb, maker, ["upgrade_to", type])
                else:
                    self._get(nb, maker)
            elif type in self.world.unit_class(maker).can_build:
                if not self.gather(t.cost, t.food_cost):
                    return
                if t.storable_resource_types:
                    meadow = self.choose(Meadow, resource_type=t.storable_resource_types[0])
                    if meadow is None or meadow.place.shortest_path_distance_to(self._builders_place()) > self.world.square_width * 3:
                        if self.nb(t):
                            return
                        else:
                            meadow = self.choose(Meadow, starting_place=self._builders_place())
                else:
                    meadow = self.choose(Meadow, starting_place=self._builders_place())
                if meadow:
                    self.order(4, maker, ["build", type, meadow.id], requisition=True, near=meadow)
            elif type in self.world.unit_class(maker).can_train:
                if (self.nb(Worker)
                    and nb > self.nb(maker) * 3
                    and self.potential(t.cost) > self.nb(maker) * 100):
                    # additional production sites
                    self.build_or_train_or_upgradeto_or_summon(maker)
                if self.gather(t.cost, t.food_cost):
                    self.order(nb, maker, ["train", type])
            elif type in self.world.unit_class(maker).can_research:
                if self.gather(t.cost, t.food_cost):
                    self.order(1, maker, ["research", type])
            else:
                for ability in self.world.unit_class(maker).can_use:
                    effect = rules.get(ability, "effect")
                    if effect and "summon" in effect[:1] and type in effect:
                        if rules.get(ability, "effect_target") == ["ask"]:
                            self.order(1, maker, ["use", ability, self.units[0].id])
                            # TODO select best place
                        else:
                            self.order(1, maker, ["use", ability])
                        break

    def _cataclysm_is_efficient(self, a, units):
        type_names = {u.type_name for u in units}
        e = rules.get(a, "effect")
        if e[0] == "summon":
            for item in e[1:]:
                if rules.get(item, "harm_level"):
                    for t in type_names:
                        if self.world.can_harm(item, t):
                            return True

    def _eventually_attack(self, places):
        units = self._idle_fighters
        if not units:
            return
        places = sorted(places, key=self.enemy_menace)
        for place in places:
            if self._units_should_attack(units, place):
                self._send_units(units, place)
                return
        if places:
            place = places[0]
            temp_units = [u for u in units if u.time_limit and u.speed]
            if temp_units:
                self._send_units(temp_units, place)
            place = places[-1]
            if not self._friendly_presence(place):
                enemies = (u for l in (self.perception, self.memory)
                                 for u in l if u.place is place and self.is_an_enemy(u))
                for u, a in self._cataclysm_users:
                    if u.orders or not self._cataclysm_is_efficient(a, enemies):
                        continue
                    path = u.place.shortest_path_to(place, places=True)
                    if len(path) > 2:
                        u.take_order(["go", path[-2].id], forget_previous=False)
                    u.take_order(["use", a, place.id], forget_previous=False)
                    if u.orders and not u.orders[0].is_impossible:
                        u.take_order(["go", u.place.id], forget_previous=False)

    @property
    def _idle_fighters(self):
        return [u for u in self.units if isinstance(u, Soldier)
                and (not u.orders
                     or len(u.orders) == 1
                        and u.orders[0].keyword == "go"
                        and u.orders[0].target not in self._enemy_presence)]

    def _update_time_has_come(self):
        self._waiting_menace = {}
        self._waiting_units = {}
        for u in self.units:
            for o in u.orders[:1]:
                if o.keyword == "wait":
                    try:
                        self._waiting_menace[o.target] += u.menace
                        self._waiting_units[o.target].append(u)
                    except:
                        self._waiting_menace[o.target] = u.menace
                        self._waiting_units[o.target] = [u]
        self._time_has_come = {}
        for place in self._waiting_units:
            self._time_has_come[place] = self._is_powerful_enough(self._waiting_units.get(place, ()), place)
        cancel = set()
        for place in self._waiting_menace:
            if not self._is_powerful_enough(self.units, place):
                for u in self.units:
                    for o in u.orders:
                        if o.keyword == "wait" and o.target is place:
                            cancel.add(u)
        for u in cancel:
            u.cancel_all_orders()

    def time_has_come(self, place):
        if place in self._cataclysmic_places:
            return False
        try:
            return self._time_has_come[place]
        except:
            return False

    def _friendly_presence(self, place):
        return place in self._places_with_friends

    def _send_units(self, units, place):
        if place is None:
            return
        units = [u for u in units if u.place != place]
        for u in units:
            u.cancel_all_orders()
        used_teleportation = False
        for u, a in self._teleportation_users:
            u.take_order(["use", a, place.id])
            if u.orders and not u.orders[0].is_impossible:
                used_teleportation = True
        enemies = (u for l in (self.perception, self.memory)
                   for u in l if u.place is place and self.is_an_enemy(u))
        for u in units:
            path = u.place.shortest_path_to(place, places=True)
            if not used_teleportation and len(path) > 2:
                u.take_order(["go", path[-2].id], forget_previous=False)
                if not self._friendly_presence(place):
                    for u_, a in self._cataclysm_users:
                        if u_ is u and self._cataclysm_is_efficient(a, enemies):
                            u.take_order(["use", a, place.id], forget_previous=False)
            #u.take_order(["wait", place.id], forget_previous=False)
            for u_, a in self._summon_users:
                if u_ is u:
                    u.take_order(["use", a, place.id], forget_previous=False)
            for u_, a in self._detector_users:
                if u_ is u:
                    u.take_order(["use", a, place.id], forget_previous=False)
            u.take_order(["go", place.id], forget_previous=False)

    def _units_should_attack(self, units, place):
        # assert units is not None
        if not self._is_powerful_enough(units, place):
            return False
        start = units[0].place
        path = start.shortest_path_to(place, places=True)
        if not path:
            return False
        elif len(path) <= 2:
            return True
        else:
            return start.shortest_path_to(path[-2], player=self, avoid=True)

    def on_unit_attacked(self, unit, attacker):
        if attacker.player in self.allied or not attacker.is_vulnerable: return
        if unit.orders and unit.orders[0].keyword == "auto_explore":
            # Don't react now. Constant attacks will do the job if active.
            # And the easy computer AI shouldn't be aggressive.
            return
        if unit.is_a_building:
            self._sensible_building = unit
        if attacker in self.perception:
            place = attacker.place
        else:
            # undetected attacker
            place = unit.place # neighbors?
        if place not in self._attacked_places:
            self._attacked_places.append(place)
