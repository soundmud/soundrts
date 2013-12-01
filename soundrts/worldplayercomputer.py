from worldplayerbase import *


class Computer(Player):

    name = "ai"
    AI_type = None
    mode = 0
    AI_timer = 0
    never_played = True
    client = None
    my_base = None
    send_timer = 0

    def __init__(self, world, client, neutral):
        self.attack_squares = []
        self.previous_choose = {}
        self.already_researched = []
        self.neutral = neutral
        if neutral:
            self.name = "npc_ai"
        Player.__init__(self, world, client)
        self.set_ai(client.AI_type)

    def set_ai(self, ai):
        self.AI_type = ai
        self._plan = get_ai(ai)
        # set or reset default values
        self._line_nb = 0
        self.retaliate = 1
        self.watchdog = 0
        self.constant_attacks = 0
        self.research = 0
        self.teleportation = 0
        self.send_soldiers_to_base = 0
        self.raise_dead = 0

    def send_update(self, l, type="maj"):
        pass

    _previous_linechange = 0
    __line_nb = 0
##    _prev_line_nb = None

    def get_line_nb(self):
        return self.__line_nb

    def set_line_nb(self, value):
        self.__line_nb = value
        self._previous_linechange = self.world.time

    _line_nb = property(get_line_nb, set_line_nb)

    def _play(self):
        if not self._plan: return
        if self.watchdog and self.world.time > \
           self._previous_linechange + self.watchdog * 1000:
            self._line_nb += 1
        self._line_nb %= len(self._plan)
        line = self._plan[self._line_nb]
        cmd = line.split()
        if cmd:
##            if self._prev_line_nb != self._line_nb:
##                print self.AI_type
##                print line
##                self._prev_line_nb = self._line_nb
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
                if VERSION[-4:] == "-dev":
                    print cmd[1]
            elif cmd[0] == "goto_random":
                dest = worldrandom.choice(cmd[1:])
                if "label " + dest in self._plan:
                    self._line_nb = self._plan.index("label " + dest)
                else:
                    warning("goto_random: label not found: %s", dest)
                    self._line_nb += 1
            elif cmd[0] == "attack":
                self.attack()
                self._line_nb += 1
            elif cmd[0] in ("retaliate", "watchdog", "constant_attacks",
                            "research", "teleportation", "send_soldiers_to_base", "raise_dead"):
                setattr(self, cmd[0], int(cmd[1]))
                self._line_nb += 1
            elif cmd[0] == "get":
                n = 1
                done = True
                for w in cmd[1:]:
                    if re.match("^[0-9]+$", w):
                        n = int(w)
                    elif w in get_rule_classnames():
                        if not self.get(n, self.equivalent(w)):
                            done = False
                            break
                    else:
                        warning("get: unknown unit: '%s' (in ai.txt)", w)
                if done:
                    self._line_nb += 1
            else:
                warning("unknown command: '%s' (in ai.txt)", cmd[0])
                self._line_nb += 1

    def build_a_warehouse_if_useful(self):
        # TODO?: a worker (or nearest_warehouse()) suggests the
        # building of a new warehouse as soon as he notices the need
        # (or nearest_warehouse() distance is too big); then the computer
        # player reads the suggestions.
        # (avoids the self.units for loop)
        # (but the current method is not so heavy after all because of the
        # "done" list; and the suggestion list would have to be pruned if
        # a deposit is not being exploited anymore)
        if self.missing_resources(self.unit_class(self.equivalent("townhall")).cost):
            return
        done = []
        for u in self.units:
            if u.orders and u.orders[0].keyword == "gather":
                deposit = u.orders[0].target
                if deposit in done:
                    continue
                else:
                    done.append(deposit)
                if deposit is not None and deposit.place is not None: # XXX a townhall even for wood?
                    wh = self.nearest_warehouse(deposit.place,
                                                deposit.resource_type)
                    if wh is None or \
                       deposit.place.shortest_path_distance_to(wh.place) > self.world.square_width:
                        meadow = self.choose(Meadow, starting_place=deposit.place)
                        if meadow:
                            for v in self.units:
                                if v.orders and v.orders[0].keyword == "gather" \
                                   and (v.orders[0].target == deposit
                                        or v.place is deposit.place) or (
                                            isinstance(v, Worker)
                                            and not v.orders):
                                    v.take_order(["build", self.equivalent("townhall"), meadow.id])
                                    v.take_order(["gather", deposit.id], forget_previous=False)
                                    self.my_base = deposit.place
                            return True

    @property
    def is_building_or_repairing(self):
        for u in self.units:
            if u.orders and u.orders[0].keyword in ["build", "repair",
                                                    "build_phase_two"]:
                return True

    idle_buildings_research_timer = 0

    def idle_buildings_research(self):
        if self.idle_buildings_research_timer > 0:
            self.idle_buildings_research_timer -= 1
            return
        else:
            self.idle_buildings_research_timer = 10
        for u in self.units:
            if not u.orders:
                for t in u.can_research:
                    if t not in self.already_researched \
                       and not self.missing_resources(self.unit_class(t).cost) \
                       and self.potential(self.unit_class(t).cost) > 3:
                        u.take_order(["research", t])
                        self.already_researched.append(t)

    def play(self):
        if self.never_played:
            self.attack_squares = [self.world.grid[name] for name in self.world.starting_squares]
            if self.units[0].place in self.attack_squares: # may not happen if additional units in other squares
                self.attack_squares.remove(self.units[0].place)
                self.my_base = self.units[0].place
            worldrandom.shuffle(self.attack_squares)
            self.never_played = False
        self.idle_peasants_gather()
        if self.constant_attacks:
            self.try_constant_attacks()
        if self.research:
            self.idle_buildings_research()
        if self.raise_dead:
            self.raise_dead_units()
        if self.send_soldiers_to_base and self.my_base is not None:
            if self.send_timer == 0:
                self.send_soldiers_to_my_base()
                self.send_timer = 40
            else:
                self.send_timer -= 1
        if self.AI_timer == 0:
            if not self.is_building_or_repairing: # XXX: not perfect (one building at a time; problems if peasants destroyed) but the AI must not be too good
                try:
                    if not self.build_a_warehouse_if_useful():
                        self._play()
                except RuntimeError: # XXX: maximum recursion (for example if no TownHall and no Peasant)
                    warning("recursion error with %s; current ai.txt line is: %s",
                            self.AI_type, self._plan[self._line_nb])
                    if VERSION[-4:] == "-dev":
                        exception("")
                    self._line_nb += 1 # go to next step; useful?
                    print "recursion error!"
                    self.AI_timer = 100 # probably not, so make a big pause
#            else:
#                self.send_some_peasants_to_building_site() # Don't know if it will be needed,
# But sometimes AI forget the building being constructed
        else:
            self.AI_timer -= 1

    def raise_dead_units(self, forget=False, place=None):
        for u in self.units:
            if place == None:
                place = u.place
            if self.raise_dead and "a_raise_dead" in u.can_use:
                if self.found_corpse(place) and u.place == place:
                    u.take_order(["use", "a_raise_dead", u.place], forget_previous = forget)

    def found_corpse(self, sq):
        for o in sq.objects:
            if isinstance(o, Corpse):
                return True
        return False

    def missing_resources(self, cost):
        result= []
        for i, c in enumerate(cost):
            if c > self.resources[i]:
                result.append(i)
        return result

    def unit_class(self, name):
        return self.world.unit_class(name)

    retry_timer_for_idle_peasant = 0

    def idle_peasants_gather(self):
        if self.retry_timer_for_idle_peasant > 0:
            self.retry_timer_for_idle_peasant -= 1
            return
        idle_peasants = [u for u in self.units if
                         isinstance(u, Worker) and not u.orders]
        if not idle_peasants:
            self.retry_timer_for_idle_peasant = 10
            return
        for u in idle_peasants:
            deposit = self.choose(Deposit, starting_place=u.place, random=True)
            if not deposit:
                self.retry_timer_for_idle_peasant = 10
                return
            u.take_order(["gather", deposit.id])

    def explore(self):
        for u in self.units:
            if u.orders and u.orders[0].keyword == "auto_explore":
                return
        maxspeed = 0
        type_name = Worker
        for u in self.units:
            if u.airground_type == "air" and u.speed > 0:
                maxspeed = u.speed
                type_name = u.type_name
                break
            if not isinstance(u, Worker) and u.speed > maxspeed:
                maxspeed = u.speed
                type_name = u.type_name
        self.order(1, type_name, ["auto_explore"], True)

    def no_enemy_in(self, place):
        for l in (self.perception, self.memory):
            for o in l:
                if o.place is place and self.is_an_enemy(o):
                    return False
        return True

    def _remove_far_candidates(self, candidates, start, limit):
        ids = dict([(o.id, o) for o in candidates])
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

    def choose(self, c, resource_type=None, nearest_for_builders=False,
               starting_place=None, random=False): # choose nearest object
        if not self.units:
            return
        k = "%s %s %s" % (c, resource_type, starting_place)
        if k in self.previous_choose and not nearest_for_builders and not random:
            candidate = self.previous_choose[k]
            if (candidate in self.perception or candidate in self.memory) \
               and candidate.place is not None \
               and (resource_type is None or
                    self.is_ok_for_warehouse(candidate.place, resource_type)
              and self.warehouse_not_already_there(candidate.place, resource_type)
                    and self.no_enemy_in(candidate.place)):
#                warning("useful cache %s %s", c, resource_type)
                return candidate
            else:
                del self.previous_choose[k]
        if starting_place is None:
            if nearest_for_builders:
                starts = {}
                for u in self.units:
                    if isinstance(u, Worker):
                        if u.place not in starts: starts[u.place] = 1
                        else: starts[u.place] += 1
                if starts:
                    starting_place = sorted(starts.items(), key=lambda x: x[1])[-1][0]
                else:
                    starting_place = self.units[0].place
            else:
                starting_place = self.units[0].place
        candidates = [o for o in self.perception + self.memory if self.check_type(o, c) and
                      o.place is not None and
                      (resource_type is None or
                       self.is_ok_for_warehouse(o.place, resource_type)
                       and self.warehouse_not_already_there(o.place, resource_type))]
        if len(candidates) > 10:
            candidates = self._remove_far_candidates(candidates, starting_place, 1)
        else:
            candidates.sort(key=lambda x: starting_place.shortest_path_distance_to(x.place))
            while candidates and starting_place.shortest_path_distance_to(candidates[0].place) is None: # None < 0
                del candidates[0] # no path
        if random:
            candidates = [o for o in candidates if self.no_enemy_in(o.place)]
            if candidates:
                p = candidates[0].place
                candidates = [o for o in candidates if o.place == p]
                worldrandom.shuffle(candidates)
        for o in candidates:
            if self.no_enemy_in(o.place):
                if not nearest_for_builders and not random:
                    self.previous_choose[k] = o
                return o
        self.explore()
        self.AI_timer = 10 # don't insist for a while

    def is_ok_for_warehouse(self, z, resource_type):
        # a resource must be there
        for o in z.objects:
            if isinstance(o, Deposit) and o.resource_type == resource_type:
                return True
        return False

    def warehouse_not_already_there(self, z, resource_type):
        # a warehouse (allied or not) must not be already there
        for o in z.objects: # XXX cheating? => no owned warehouse and no remembered enemy?
            if resource_type in getattr(o, "storable_resource_types", ()):
                return False
        return True

    def order(self, nb, types, order, replace=False):
        self.AI_timer = 10 # XXX: compute value # don't use ai too often # TODO: use events, not this timer
        if nb == "all":
            nb = 9999
        for u in self.units:
            if self.check_type(u, types):
                if nb <= 0:
                    return
                # XXX: research and improvements not implemented
                # no need to queue more than one order (XXX but AI_timer...)
                if replace or not (u.orders and u.orders[-1].keyword == order[0]):
                    u.take_order(order)
                # order given or already given
                nb -= 1

    def potential(self, cost):
        result = 9999
        for i, res in enumerate(self.resources):
            if cost[i]:
                result = min(result, res / cost[i])
        return result

    def get(self, nb, types):
        self._safe_cnt = 0
        return self._get(nb, types)

    def _get(self, nb, types):
        self._safe_cnt += 1
        if self._safe_cnt > 10:
            print "*** safe ***"
            self.AI_timer = 100
            return False
        if isinstance(types, str):
            types = [types]
        if self.nb(types) >= nb:
            return True
        for type in types:
            if type.__class__ == str:
                type = self.world.unit_class(type)
            if type is None:
                continue
            if self.nb(self.world.get_makers(type)) > 0:
                self.build_or_train_or_upgradeto(type, nb - self.nb(types))
                break
            elif self.world.get_makers(type):
                self._get(1, self.world.get_makers(type)[0])
                return False
        return False

    gather_mode = None

    def gather(self, cost, food): # XXX: too slow? called too often?
        for i in self.missing_resources(cost):
            if self.gather_mode != i:
                r = self.choose(self.world.get_deposits(i))
                if r:
                    self.order(max(1, self.nb(Worker) * 8 / 10),
                               Worker, ["gather", r.id], True)
                    self.gather_mode = i
                else:
                    self.AI_timer = 10
            return
        if food != 0 and food > self.food - self.used_food:
            self.build_or_train_or_upgradeto(self.equivalent("farm"))
            self.gather_mode = None
        else:
            self.gather_mode = None
            return True

    def on_resource_exhausted(self):
        self.gather_mode = None

    def on_unit_flee(self, unit):
        self.gather_mode = None
        if isinstance(unit, Worker): # XXX pb if no archers and enemy==dragons
            self.on_unit_attacked(unit)

    def send_some_peasants_to_building_site(self):
        bs = None
        for u in self.units:
            if isinstance(u, BuildingSite):
                bs = u
                break
        if bs is not None:
            self.order(8, Worker, ["repair", bs.id], True)

    def _get_requirements(self, t):
        for r in t.requirements:
            if not self._get(1, r):
                return False
        return True

    def build_or_train_or_upgradeto(self, t, nb=1):
        if t.__class__ == str:
            t = self.world.unit_class(t)
        type = t.__name__
        if self.gather(t.cost, t.food_cost) and \
           self._get(1, self.world.get_makers(type)) and \
           self._get_requirements(t):
            # XXX why choose the first maker type? (problem if several creation paths are possible (train and upgradeto for example))
            if type in self.world.unit_class(self.world.get_makers(type)[0]).can_upgrade_to:
                # upgrade to
                if self.nb(self.world.get_makers(type)[0]) >= nb:
                    # If we have the correct number of archers,
                    # We upgrade then here.
                    self.order(nb, self.world.get_makers(type)[0], ["upgrade_to", type])
                    self.AI_timer = 100 # XXX: compute value # don't use ai too often # TODO: use events, not this timer
                else:
                    # If not, we recruit then
                    self._get(nb, self.world.get_makers(type)[0])
            elif type in self.world.unit_class(self.world.get_makers(type)[0]).can_build:
                # build
                if self.nb(BuildingSite) > 0:
                    self.send_some_peasants_to_building_site()
                    return
                if t.storable_resource_types:
                    meadow = self.choose(Meadow, resource_type=t.storable_resource_types[0])
                    # if no place to build and already enough building, forget this
                    if meadow is None:
                        if self.nb(t) > 0:
                            return True
                        else:
                            meadow = self.choose(Meadow)
                else:
                    meadow = self.choose(Meadow, nearest_for_builders=True)
                if meadow:
                    self.order(8, self.world.get_makers(type), ["build", type, meadow.id], True)
                else:
                    self.AI_timer = 10
                    return
            elif type in self.world.unit_class(self.world.get_makers(type)[0]).can_train:
                # train
                if self.nb(Worker) and \
                   nb > self.nb(self.world.get_makers(type)[0]) * 3 and \
                   self.potential(t.cost) > \
                   self.nb(self.world.get_makers(type)[0]) * 100:
                    # additional production sites
                    self.build_or_train_or_upgradeto(self.world.get_makers(type)[0])
                self.order(nb, self.world.get_makers(type), ["train", type])
        else:
            self.AI_timer = 100 # XXX: compute value # don't use ai too often # TODO: use events, not this timer
            debug("not enough")

    def attack(self, all=False):
        if all:
            types = self.world.get_units()
        else:
            types = self.world.get_soldiers()
        for t in types:
            self.order("all", t, ["auto_attack"])

    def enemy_menace(self, place):
        if self._enemy_menace_time.get(place) != self.world.time:
            enemy_menace = 0
            for l in (self.perception, self.memory):
                for o in l:
                    if o.place == place and self.is_an_enemy(o):
                        enemy_menace += o.menace + .0001 # must be attacked anyway
            self._enemy_menace[place] = enemy_menace
            self._enemy_menace_time[place] = self.world.time
        return self._enemy_menace[place]

    def menace(self):
        menace = 0
        for u in self.units:
            if u.speed > 0 and isinstance(u, Soldier):
                menace += u.menace
        return menace

    def is_powerful_enough(self, place):
        return self.menace() > self.enemy_menace(place) * 2

    def send_idle_fighters(self, place):
        for u in self.units:
            if isinstance(u, Soldier) and not u.orders:
                if self.teleportation and "a_teleportation" in u.can_use:
                    u.take_order(["use", "a_teleportation", place.id])
                u.take_order(["go", place.id], forget_previous=False)

    AI_constant_attacks_timer = 0

    def can_attack(self):
        for p in self.attack_squares:
            if not self.is_powerful_enough(p):
                return False
        return True

    def try_constant_attacks(self):
        if self.AI_constant_attacks_timer:
            self.AI_constant_attacks_timer -= 1
        else:
            if not self.attack_squares:
                self.attack_squares = [p for p in self.world.squares
                                       if self.enemy_menace(p)]
            for p in self.attack_squares[:]:
                if not self.enemy_menace(p):
                    if p in self.observed_before_squares:
                        self.attack_squares.remove(p)
            if self.can_attack() and self.attack_squares:
                self.send_idle_fighters(self.attack_squares[0])
            if not self.attack_squares:
                self.explore()
            self.AI_constant_attacks_timer = 10

    def on_unit_attacked(self, unit, attacker=None):
        if unit.is_an_explorer:
            # Don't react now. Constant attacks will do the job if active.
            # And the easy computer AI shouldn't be aggressive.
            return
        if attacker is not None:
            place = attacker.place
        else:
            place = unit.place
        if self.retaliate and self.is_powerful_enough(place) and self.can_attack():
            self.send_idle_fighters(place)
            self.my_base = place # For now, send the soldiers to this place,
            # If we're being attacked here.
        if self.raise_dead:
            self.raise_dead_units(forget=True, place=place)
            # This is for AI continuously make zombies, because it only
            # makes while not in the fight, what we don't want
        if place not in self.attack_squares:
            self.attack_squares.append(place)

    def update_attack_squares(self, unit):
        if unit.is_an_enemy(unit.cible):
            if unit.place not in self.attack_squares:
                self.attack_squares.append(unit.place)
        else:
            if unit.place in self.attack_squares:
                self.attack_squares.remove(unit.place)

    def send_soldiers_to_my_base(self):
        # This function orders all soldiers to go to the base.
        # send_idle_fighters() will take mana, so we
        # order all go instead of teleport.
        for u in self.units:
            if isinstance(u, Soldier) and not u.orders:
                if u.place != self.my_base:
                    u.take_order(["go", self.my_base.id], forget_previous=False)
