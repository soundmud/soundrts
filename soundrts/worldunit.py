import worldrandom

from constants import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL, DEFAULT_MINIMAL_DAMAGE
from definitions import rules
from lib.log import debug, warning, exception
from lib.nofloat import PRECISION, square_of_distance, int_cos_1000, int_sin_1000, int_angle, int_distance
from worldaction import Action, AttackAction, MoveAction, MoveXYAction
from worldentity import Entity
from worldorders import ORDERS_DICT, GoOrder, RallyingPointOrder, BuildPhaseTwoOrder, UpgradeToOrder
from worldresource import Corpse, Deposit


class Creature(Entity):

    type_name = None

    def get_action_target(self):
        if self.action:
            return self.action.target

    def set_action_target(self, value):
        if isinstance(value, tuple):
            self.action = MoveXYAction(self, value)
        elif self.is_an_enemy(value):
            self.action = AttackAction(self, value)
        elif value is not None:
            self.action = MoveAction(self, value) # "use" ?
        else:
            self.action = Action(self, value)

    action_target = property(get_action_target, set_action_target)

    hp_max = 0
    hp_regen = 0
    mana_max = 0
    mana_start = 0
    mana_regen = 0
    walked = []

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    time_cost = 0
    food_cost = 0
    food_provided = 0
    is_fleeing = False
    ai_mode = None
    can_switch_ai_mode = False
    storable_resource_types = ()
    storage_bonus = ()

    is_buildable_anywhere = True

    transport_capacity = 0
    transport_volume = 1

    requirements = ()
    is_a = ()
    can_build = ()
    can_train = ()
    can_use = ()
    can_research = ()
    can_upgrade_to = ()

    armor = 0
    damage = 0
    damage_level = 0

    basic_abilities = []

    is_vulnerable = True
    is_healable = True
    is_a_gate = False
    provides_survival = False

    damage_radius = 0
    target_types = ["ground"]
    range = None
    is_ballistic = 0
    minimal_range = 0
    cooldown = 0
    next_attack_time = 0
    splash = False

    player = None
    number = None

    expanded_is_a = ()

    time_limit = None
    rallying_point = None

    corpse = 1
    decay = 0

    presence = 1

    is_an_explorer = False

    count_limit = 0

    def next_free_number(self):
        numbers = [u.number for u in self.player.units if u.type_name == self.type_name and u is not self]
        n = 1
        while n in numbers:
            n += 1
        return n

    def set_player(self, player):
        # stop current action
        self.action_target = None
        self.cancel_all_orders(unpay=False)
        # remove from previous player
        if self.player is not None:
            self.player.units.remove(self)
            self.player.food -= self.food_provided
            self.player.used_food -= self.food_cost
            self.update_all_dicts(-1)
        # add to new player
        self.player = player
        if player is not None:
            self.number = self.next_free_number()
            player.units.append(self)
            self.player.food += self.food_provided
            self.player.used_food += self.food_cost
            self.update_all_dicts(1)
            self.upgrade_to_player_level()
            # player units must stop attacking the "not hostile anymore" unit
            for u in player.units:
                if u.action_target is self:
                    u.action_target = None
        # update perception of object by the players
        if self.place is not None:
            self.update_perception()
        # if transporting units, set player for them too
        for o in self.objects:
            o.set_player(player)

    def __init__(self, prototype, player, place, x, y, o=90):
        if prototype is not None:
            prototype.init_dict(self)
        self.orders = []
        # transport data
        self.objects = []
        self.world = place.world # XXXXXXXXXX required by transport

        # set a player
        self.set_player(player)

        # stats "with a max"
        self.hp = self.hp_max
        if self.mana_start > 0:
            self.mana = self.mana_start
        else:
            self.mana = self.mana_max

        # stat defined for the whole game
        self.minimal_damage = rules.get("parameters", "minimal_damage")
        if self.minimal_damage is None:
            self.minimal_damage = DEFAULT_MINIMAL_DAMAGE

        # move to initial place
        Entity.__init__(self, place, x, y, o)

        if self.decay:
            self.time_limit = self.world.time + self.decay

    def upgrade_to_player_level(self):
        for upg in self.can_use:
            if upg in self.player.upgrades:
                self.player.world.unit_class(upg).upgrade_unit_to_player_level(self)

    @property
    def upgrades(self):
        return [u for u in self.can_use if u in self.player.upgrades]

    def contains_enemy(self, player): # XXXXXXXXXX required by transport
        return False

    @property
    def height(self):
        if self.airground_type == "air":
            return 2
        else:
            return self.place.height + self.bonus_height

    def get_observed_squares(self):
        if self.is_inside or self.place is None:
            return []
        result = [self.place]
        for sq in self.place.neighbours:
            # Blockers (walls, etc) are ignored for now because if a blocker disappears
            # it would be necessary to update the player's perception.
            if self.height > sq.height \
            or self.height == sq.height and self._can_go(sq.x, sq.y, ignore_blockers=True):
                result.append(sq)
        return result

    @property
    def menace(self):
        return self.damage

    @property
    def activity(self):
        if not self.orders:
            return
        o = self.orders[0]
        if hasattr(o, "mode") and o.mode == "build":
            return "building"
        if hasattr(o, "mode") and o.mode == "gather" and hasattr(o.target, "type_name"):
            return "exploiting_%s" % o.target.type_name

    # reach (avoiding collisions)

    def _already_walked(self, x, y):
        n = 0
        radius_2 = self.radius * self.radius
        for lw, xw, yw, weight in self.walked:
            if self.place is lw and square_of_distance(x, y, xw, yw) < radius_2:
                n += weight
        return n

    def _future_coords(self, rotation, target_d):
        d = self.speed * VIRTUAL_TIME_INTERVAL / 1000
        if rotation == 0:
            d = min(d, target_d) # stop before colliding target
        a = self.o + rotation
        x = self.x + d * int_cos_1000(a) / 1000
        y = self.y + d * int_sin_1000(a) / 1000
        return x, y

    def _heuristic_value(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        return abs(rotation) + self._already_walked(x, y) * 200

    def _can_go(self, x, y, ignore_blockers=False):
        if self.airground_type != "ground":
            return True
        new_place = self.world.get_place_from_xy(x, y)
        if new_place is self.place:
            return True
        for e in self.place.exits:
            if e.other_side.place is new_place:
                if ignore_blockers:
                    return True
                if e.is_blocked(self):
                    for o in e.blockers:
                        self.player.observe(o)
                else:
                    return True

    def _try(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        if self.place.contains(x, y) and not self.would_collide_if(x, y):
            if abs(rotation) >= 90:
                self.walked.append([self.place, self.x, self.y, 5]) # mark the dead end
            self.move_to(self.place, x, y, self.o + rotation)
            self.unblock()
            return True
        elif not self.place.contains(x, y) and self._can_go(x, y) and not self.would_collide_if(x, y):
            if abs(rotation) >= 90:
                self.walked.append([self.place, self.x, self.y, 5]) # mark the dead end
            new_place = self.world.get_place_from_xy(x, y)
            self.move_to(new_place, x, y, self.o + rotation)
            self.unblock()
            return True
        return False

    _rotations = None
    _smooth_rotations = None

    def _reach(self, target_d):
        if self._smooth_rotations:
            # "smooth rotation" mode
            rotation = self._smooth_rotations.pop(0)
            if self._try(rotation, target_d) or self._try(-rotation, target_d):
                self._smooth_rotations = []
        else:
            if not self._rotations:
                # update memory
                self.walked = [x[0:3] + [x[3] - 1] for x in self.walked if x[3] > 1]
                # "go straight" mode
                if not self.walked and self._try(0, target_d): return
                # enter "rotation mode"
                self._rotations = [(self._heuristic_value(x, target_d), x) for x in
                          (0, 45, -45, 90, -90, 135, -135, 180)]
                self._rotations.sort()
            # "rotation" mode
            for _ in range(min(4, len(self._rotations))):
                _, rotation = self._rotations.pop(0)
                if self._try(rotation, target_d):
                    self._rotations = []
                    return
            if not self._rotations:
                # enter "smooth rotation mode"
                self._smooth_rotations = range(1, 180, 1)
                self.walked = []
                self.walked.append([self.place, self.x, self.y, 5]) # mark the dead end
                self.notify("collision")

    # go center

    def _go_center(self):
        self.action_target = (self.place.x, self.place.y)

    def _near_enough_to_use(self, target):
        if self.is_an_enemy(target):
            # Melee units (range <= 2) shouldn't attack units
            # on the other side of a wall.
            if not self._can_go(target.x, target.y) \
                and self.range <= 2 * PRECISION \
                and not target.blocked_exit:
                    return False
            if self.minimal_range and square_of_distance(self.x, self.y, target.x, target.y) < self.minimal_range * self.minimal_range:
                return False
            d = target.use_range(self)
            return square_of_distance(self.x, self.y, target.x, target.y) < d * d
        elif target.place is self.place:
            d = target.use_range(self)
            return square_of_distance(self.x, self.y, target.x, target.y) < d * d

    def be_used_by(self, actor):
        if actor.is_an_enemy(self):
            actor.aim(self)

    # reach and use

    def action_reach_and_use(self):
        target = self.action_target
        if not self._near_enough_to_use(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y) # turn toward the goal
            self._reach(d - target.collision_range(self))
        else:
            self.walked = []
            target.be_used_by(self)

    def go_to_xy(self, x, y):
        d = int_distance(self.x, self.y, x, y)
        if d > self.radius:
            # execute action
            self.o = int_angle(self.x, self.y, x, y) # turn towards the goal
            self._reach(d)
        else:
            return True

    # update

    def has_imperative_orders(self):
        return self.orders and self.orders[0].is_imperative

    def _execute_orders(self):
        queue = self.orders
        if queue[0].is_complete or queue[0].is_impossible:
            queue.pop(0)
        else:
            queue[0].update()

    def _is_attacking(self):
        return isinstance(self.action, AttackAction)

    def update(self):
        assert isinstance(self.hp, (int, long))
        assert isinstance(self.mana, (int, long))
        assert isinstance(self.x, int)
        assert isinstance(self.y, int)
        assert isinstance(self.o, int)

        self.is_moving = False

        # do nothing if inside
        if self.is_inside:
            return
        # passive level (aura)
        if self.heal_level:
            self.heal_nearby_units()
        if self.harm_level:
            self.harm_nearby_units()
        # action level
        if self.action:
            self.action.update()
        # order level (warning: completing UpgradeToOrder deletes the object)
        if self.has_imperative_orders():
            self._execute_orders()
        else:
            # TODO: use triggers (to optimize)
            if not self._is_attacking():
                self.choose_enemy()
            # execute orders if the unit is not fighting (targeting an enemy)
            if self.orders and not self._is_attacking():
#            # experimental: execute orders if no current action
#            if self.orders and not self.action_type:
                self._execute_orders()

    # slow update

    def regenerate(self):
        if self.hp_regen and self.hp < self.hp_max:
            self.hp = min(self.hp_max, self.hp + self.hp_regen)
        if self.mana_regen and self.mana < self.mana_max:
            self.mana = min(self.mana_max, self.mana + self.mana_regen)

    def slow_update(self):
        self.regenerate()
        if self.time_limit is not None and self.place.world.time >= self.time_limit:
            self.die()

    def receive_hit(self, damage, attacker, notify=True):
        self.hp -= damage
        if self.hp < 0:
            self.die(attacker)
        else:
            self.on_wounded(attacker, notify)

    def delete(self):
        # delete first, because if self.player is None the player will miss the
        # deletion and keep a memory of his own deleted unit
        Entity.delete(self)
        self.set_player(None)

    def die(self, attacker):
        for o in self.objects[:]:
            o.move_to(self.place, self.x, self.y)
            if o.place is self: # not enough space
                o.collision = 0
                o.move_to(self.place, self.x, self.y)
            if self.airground_type == "air":
                o.die(attacker)
        self.notify("death")
        if attacker is not None:
            self.notify("death_by,%s" % attacker.id)
        self.player.on_unit_attacked(self, attacker)
        for u in self.place.objects:
            u.react_death(self)
        self.delete()

    heal_level = 0

    def heal_nearby_units(self):
        # level 1 of healing: 1 hp every 7.5 seconds
        hp = self.heal_level * PRECISION / 25
        for p in self.player.allied:
            for u in p.units:
                if u.is_healable and u.place is self.place:
                    if u.hp < u.hp_max:
                        u.hp = min(u.hp_max, u.hp + hp)

    harm_level = 0
    harm_target_type = ()

    def can_harm(self, other):
        d = self.world.harm_target_types
        k = (self.type_name, other.type_name)
        if k not in d:
            result = True
            for t in self.harm_target_type:
                if t == "healable" and not other.is_healable or \
                   t == "building" and not isinstance(other, _Building) or \
                   t in ("air", "ground") and other.airground_type != t or \
                   t == "unit" and not isinstance(other, Unit) or \
                   t == "undead" and not other.is_undead:
                    result = False
                    break
            d[k] = result
        return d[k]

    def harm_nearby_units(self):
        # level 1: 1 hp every 7.5 seconds
        hp = self.harm_level * PRECISION / 25
        for u in self.place.objects:
            if u.is_vulnerable and self.can_harm(u):
                u.receive_hit(hp, self, notify=False)

    def is_an_enemy(self, c):
        if isinstance(c, Creature):
            if self.has_imperative_orders() and \
               self.orders[0].__class__ == GoOrder and \
               self.orders[0].target is c:
                return True
            else:
                return self.player.is_an_enemy(c.player)
        else:
            return False

    # choose enemy

    def can_attack_if_in_range(self, other):
        if self.is_inside:
            return False
        if other not in self.player.perception:
            return False
        if other is None \
           or getattr(other, "hp", 0) < 0 \
           or getattr(other, "airground_type", None) not in self.target_types:
            return False
        if not other.is_vulnerable:
            return False
        return True

    def can_attack(self, other): # without moving to another square
        # assert other in self.player.perception # XXX false
        # assert not self.is_inside # XXX not sure

        if not self.can_attack_if_in_range(other):
            return False
        if self.range and other.place is self.place:
            return True
        if self.place.is_near(other.place):
            return self._near_enough_to_use(other)

##    def _can_be_reached_by(self, player):
##        for u in player.units:
##            if u.can_attack(self):
##                return True
##        return False

    def _choose_enemy(self, place):
        known = self.player.known_enemies(place)
        reachable_enemies = [x for x in known if self.can_attack(x)]
        if reachable_enemies:
            reachable_enemies.sort(key=lambda x: (- x.value, square_of_distance(self.x, self.y, x.x, x.y), x.id))
            self.action_target = reachable_enemies[0] # attack nearest
            self.notify("attack") # XXX move this into set_action_target()?
            return True
##        else:
##            for u in enemy_units:
##                if u.can_attack(self) and not u._can_be_reached_by(self.player):
##                    self.flee()
##                    return

    def choose_enemy(self, someone=None):
        if self.has_imperative_orders() or self.is_fleeing:
            return
        if not self.damage:
            return
        if getattr(self.action_target, "menace", 0):
            return
        if someone is not None and self.can_attack(someone):
            self.action_target = someone
            self.notify("attack") # XXX move this into set_action_target()?
            return
        # _choose_enemy requires that self.player is not None
        if self.player is None:
            warning("in choose_enemy: %s.player is None", self)
            return
        if self._choose_enemy(self.place):
            return
        for p in self.place.neighbours:
            if self._choose_enemy(p):
                break

    #

    def on_wounded(self, attacker, notify):
        if self.player is not None:
            self.player.observe(attacker)
        if notify:
            self.notify("wounded,%s,%s,%s" % (attacker.type_name, attacker.id, attacker.damage_level))
        # react only if this is an external attack
        if self.player is not attacker.player and \
           attacker.is_vulnerable and \
           attacker in self.player.perception:
            self.player.on_unit_attacked(self, attacker)
            for u in self.player.units:
                if u.place == self.place:
                    u.on_friend_unit_attacked(attacker)

    def on_friend_unit_attacked(self, attacker):
        if self.has_imperative_orders() or self.is_fleeing:
            return
        if getattr(self.action_target, "menace", 0) < attacker.menace:
            if self.can_attack(attacker):
                self.action_target = attacker
            elif not self.orders and self.place.is_near(attacker.place):
                self.take_default_order(attacker.id)
                self.take_order(("go", "zoom-%s-%s-%s" %
                     (self.place.name, self.x, self.y)),
                     forget_previous=False)

    def react_death(self, creature):
        if self.action_target == creature:
            self.action_target = None
            self.choose_enemy()
            self.player.update_attack_squares(self) # XXXXXXX ?
        elif self.place == creature.place:
            self._flee_or_fight()

    def react_departure(self, someone, unused_door):
        if someone == self.action_target:
            self.action_target = None
            self.choose_enemy() # choose another enemy

    def _flee_or_fight_if_enemy(self):
        if self.place.contains_enemy(self.player):
            self._flee_or_fight()

    def _flee_or_fight(self, someone=None):
        if self.has_imperative_orders() or self.is_fleeing:
            return
        if self.ai_mode == "defensive":
            if self.place.balance(self.player) >= 0:
                self.choose_enemy(someone)
            else:
                self.flee(someone)
        elif self.ai_mode == "offensive":
            self.choose_enemy(someone)

    def react_arrival(self, someone):
        if self.place is someone.place:
            self._flee_or_fight(someone)

    def flee(self, someone=None):
        self.notify("flee")
        self.player.on_unit_flee(self)
        self.orders = []
        if self.place.exits:
            def menace(e):
                return (- e.other_side.place.balance(self.player), e.id)
            self.action_target = sorted(self.place.exits, key=menace)[0]
        self.is_fleeing = True

    def react_self_arrival(self):
        if self.is_fleeing:
            self.is_fleeing = False
            self._go_center() # don't block the passage
        self._flee_or_fight_if_enemy()
        self.notify("enter_square")
        self.player.update_attack_squares(self)

    # attack

    def hit(self, target):
        damage = max(self.minimal_damage, self.damage - target.armor)
        target.receive_hit(damage, self)

    def splash_aim(self, target):
        damage_radius_2 = self.damage_radius * self.damage_radius
        for o in target.place.objects[:]:
            if not self.is_an_enemy(o):
                pass  # no friendly fire
            elif isinstance(o, Creature) \
               and square_of_distance(o.x, o.y, target.x, target.y) <= damage_radius_2 \
               and self.can_attack_if_in_range(o):
                self.hit(o)

    def aim(self, target):
        if self.can_attack(target) and self.place.world.time >= self.next_attack_time:
            self.next_attack_time = self.place.world.time + self.cooldown
            self.notify("launch_attack")
            if self.splash:
                self.splash_aim(target)
            else:
                self.hit(target)

    # orders

    def take_order(self, o, forget_previous=True, imperative=False, order_id=None):
        if self.is_inside:
            self.place.notify("order_impossible")
            return
        cls = ORDERS_DICT.get(o[0])
        if cls is None:
            warning("unknown order: %s", o)
            return
        if not cls.is_allowed(self, *o[1:]):
            self.notify("order_impossible")
            debug("wrong order to %s: %s", self.type_name, o)
            return
        if forget_previous and not cls.never_forget_previous:
            self.cancel_all_orders()
        order = cls(self, o[1:])
        order.id = order_id
        if imperative:
            order.is_imperative = imperative
        order.immediate_action()

    def get_default_order(self, target_id):
        if target_id and target_id.startswith("zoom"):
            return "go"
        target = self.player.get_object_by_id(target_id)
        if not target:
            return
        elif getattr(target, "is_an_exit", False):
            return "block"
        elif getattr(target, "player", None) is self.player and self.have_enough_space(target):
            return "load"
        elif getattr(target, "player", None) is self.player and target.have_enough_space(self):
            return "enter"
        elif "gather" in self.basic_abilities and isinstance(target, Deposit):
            return "gather"
        elif (isinstance(target, BuildingSite) and target.type.__name__ in self.can_build or
             hasattr(target, "is_repairable") and target.is_repairable and target.hp < target.hp_max and self.can_build) \
             and not self.is_an_enemy(target):
            return "repair"
        elif RallyingPointOrder.is_allowed(self):
            return "rallying_point"
        elif GoOrder.is_allowed(self):
            return "go"

    def take_default_order(self, target_id, forget_previous=True, imperative=False, order_id=None):
        order = self.get_default_order(target_id)
        if order:
            self.take_order([order, target_id], forget_previous, imperative, order_id)

    def check_if_enough_resources(self, cost, food=0):
        for i, c in enumerate(cost):
            if self.player.resources[i] < c:
                return "not_enough_resource_%s" % i
        if not self.orders and food > 0 and self.player.available_food < self.player.used_food + food:
            if self.player.available_food < self.player.world.food_limit:
                return "not_enough_food"
            else:
                return "population_limit_reached"

    # cancel production

    def cancel_all_orders(self, unpay=True):
        while self.orders:
            self.orders.pop().cancel(unpay)

    def must_build(self, order):
        for o in self.orders:
            if o == order:
                return True

    def _put_building_site(self, type, target):
        place, x, y, _id = target.place, target.x, target.y, target.id # remember before deletion
        if not hasattr(place, "place"): # target is a square
            place = target
        if not (getattr(target, "is_an_exit", False)
                or type.is_buildable_anywhere):
            target.delete() # remove the meadow replaced by the building
            remember_land = True
        else:
            remember_land = False
        site = BuildingSite(self.player, place, x, y, type)
        if remember_land:
            site.building_land = target
        if getattr(target, "is_an_exit", False):
            site.block(target)

        # update the orders of the workers
        order = self.orders[0]
        for unit in self.player.units:
            if unit is self:
                continue
            for n in range(len(unit.orders)):
                try:
                    if unit.orders[n] == order:
                        # why not before: unit.orders[n].cancel() ?
                        unit.orders[n] = BuildPhaseTwoOrder(unit, [site.id]) # the other peasants help the first one
                        unit.orders[n].on_queued()
                except: # if order is not a string?
                    exception("couldn't check unit order")
        self.orders[0] = BuildPhaseTwoOrder(self, [site.id])
        self.orders[0].on_queued()

    # be repaired

    def _delta(self, total, percentage):
        # (percentage / 100) * total / (self.time_cost / VIRTUAL_TIME_INTERVAL) # (reordered for a better precision)
        delta = int(total * percentage * VIRTUAL_TIME_INTERVAL / self.time_cost / 100)
        if delta == 0 and total != 0:
            warning("insufficient precision (delta: %s total: %s)", delta, total)
        return delta

    @property
    def hp_delta(self):
        return self._delta(self.hp_max, 70)

    @property
    def repair_cost(self):
        return (self._delta(c, 30) for c in self.cost)

    def be_built(self): # TODO: when allied players, the unit's player should pay, not the building's
        if self.hp < self.hp_max:
            result = self.check_if_enough_resources(self.repair_cost)
            if result is not None:
                self.notify("order_impossible,%s" % result)
            else:
                self.player.pay(self.repair_cost)
                self.hp = min(self.hp + self.hp_delta, self.hp_max)

    @property
    def is_fully_repaired(self):
        return getattr(self, "is_repairable", False) and self.hp == self.hp_max

    # transport

    def have_enough_space(self, target):
        s = self.transport_capacity
        for u in self.objects:
            s -= u.transport_volume
        return s >= target.transport_volume

    def load(self, target):
        target.cancel_all_orders()
        target.notify("enter")
        target.move_to(self, 0, 0)

    def load_all(self):
        for u in sorted(self.player.units, key=lambda x: x.transport_volume, reverse=True):
            if u.place is self.place and self.have_enough_space(u):
                self.load(u)

    def unload_all(self):
        for o in self.objects[:]:
            o.move_to(self.place, self.x, self.y)
            o.notify("exit")


class Unit(Creature):

    food_cost = 1
    value = 1

    is_cloakable = True
    is_a_gate = True

    def __init__(self, player, place, x, y, o=90):
        Creature.__init__(self, player, place, x, y, o)
        self.player.nb_units_produced += 1

    def next_stage(self, target):
        if target is None or target.place is None:
            return None
        if self.airground_type == "air":
            return target
        elif target.place is not self.place.world: # target is not a square
            if self.place == target.place:
                return target
            return self.place.shortest_path_to(target.place, self)
        else: # target is a square
            if self.place == target:
                return None
            return self.place.shortest_path_to(target, self)

    def die(self, attacker=None):
        self.player.nb_units_lost += 1
        if attacker:
            attacker.player.nb_units_killed += 1
        if self.corpse:
            Corpse(self)
        Creature.die(self, attacker)

    def next_stage_enemy(self):
        for e in self.place.exits:
            if e.other_side.place.contains_enemy(self.player):
                return e
        if not self.player.attack_squares:
            self.player.attack_squares.append(
                worldrandom.choice([x for x in self.player.world.squares
                                    if x.exits and x != self.place]))
        return self.next_stage(self.player.attack_squares[0])

    def auto_explore(self):
        if not self.action_target:
            if self.place in self.player.places_to_explore:
                self.player.places_to_explore.remove(self.place)
            # level 1
            for e in self.place.exits:
                p = e.other_side.place
                if p not in self.player.observed_before_squares and \
                   p not in self.player.places_to_explore:
                    self.player.places_to_explore.append(p)
            # level 2: useful for air units
            for e in self.place.exits:
                p = e.other_side.place
                for e2 in p.exits:
                    p2 = e2.other_side.place
                    if p2 not in self.player.observed_before_squares and \
                       p2 not in self.player.places_to_explore:
                        self.player.places_to_explore.append(p2)
            if self.player.places_to_explore:
                for place in self.player.places_to_explore[:]:
                    if place in self.player.observed_before_squares:
                        self.player.places_to_explore.remove(place)
                    else:
                        self.action_target = self.next_stage(place)
                        break
            else:
                self.player.places_to_explore = [p
                     for p in self.player.world.squares
                     if p not in self.player.observed_before_squares
                     and self.next_stage(p)]
                worldrandom.shuffle(self.player.places_to_explore)
                if not self.player.places_to_explore:
                    return True

    cargo = None

    @property
    def basic_abilities(self):
        for o in self.orders:
            if isinstance(o, UpgradeToOrder):
                return []
        return self._basic_abilities

    def move_on_border(self, e):
        self.move_to(e.place, e.x, e.y)

    def block(self, e):
        if not self.blocked_exit:
            self.blocked_exit = e
            e.add_blocker(self)


class Worker(Unit):

    value = 0 # not 0.1 to avoid "combat 1 against 10" (misleading) XXX
    ai_mode = "defensive"
    can_switch_ai_mode = True
    _basic_abilities = ["go", "gather", "repair", "block"]
    is_teleportable = True


class Soldier(Unit):

    ai_mode = "offensive"
    can_switch_ai_mode = True
    _basic_abilities = ["go", "patrol", "block"]
    is_teleportable = True


class Effect(Unit):
    collision = 0
    corpse = 0
    food_cost = 0
    is_vulnerable = 0
    presence = 0
    _basic_abilities = []


class _Building(Creature):

    value = 0
    ai_mode = "offensive"
    can_switch_ai_mode = False # never flee

    is_repairable = True
    is_healable = False

    transport_volume = 99

    corpse = 0

    def __init__(self, prototype, player, square, x=0, y=0):
        Creature.__init__(self, prototype, player, square, x, y)

    def on_friend_unit_attacked(self, attacker):
        pass

    def die(self, attacker=None):
        self.player.nb_buildings_lost += 1 # all cancelled buildings lost? after resign?
        if attacker:
            attacker.player.nb_buildings_killed += 1
        place, x, y = self.place, self.x, self.y
        Creature.die(self, attacker)
        if self.building_land:
            self.building_land.move_to(place, x, y)

    def flee(self, someone=None):
        pass


class BuildingSite(_Building):

    type_name = "buildingsite"
    basic_abilities = ["cancel_building"]

    def __init__(self, player, place, x, y, building_type):
        player.pay(building_type.cost)
        _Building.__init__(self, None, player, place, x, y)
        self.type = building_type
        self.hp_max = building_type.hp_max
        self._starting_hp = building_type.hp_max * 5 / 100
        self.hp = self._starting_hp
        self.timer = building_type.time_cost / VIRTUAL_TIME_INTERVAL
        self.damage_during_construction = 0

    def receive_hit(self, damage, attacker, *args, **kargs):
        self.damage_during_construction += damage
        _Building.receive_hit(self, damage, attacker, *args, **kargs)

    @property
    def is_buildable_anywhere(self):
        return self.type.is_buildable_anywhere

    @property
    def is_buildable_on_exits_only(self):
        return self.type.is_buildable_on_exits_only

    @property
    def is_a_gate(self):
        return self.type.is_a_gate

    @property
    def time_cost(self):
        return self.type.time_cost

    @property
    def hp_delta(self):
        return self._delta(self.hp_max - self._starting_hp, 100)

    def be_built(self):
        self.hp = min(self.hp + self.hp_delta, self.hp_max)
        self.timer -= 1
        if self.timer == 0:
            player, place, x, y, hp = self.player, self.place, self.x, self.y, self.hp
            blocked_exit = self.blocked_exit
            self.delete()
            building = self.type(player, place, x, y)
            building.building_land = self.building_land
            if blocked_exit:
                building.block(blocked_exit)
            building.hp = self.type.hp_max - self.damage_during_construction
            building.notify("complete")

    @property
    def is_fully_repaired(self):
        return False


class Building(_Building):

    is_buildable_anywhere = False
    is_buildable_on_exits_only = False
    provides_survival = True

    def __init__(self, prototype, player, place, x, y):
        _Building.__init__(self, prototype, player, place, x, y)
        self.player.nb_buildings_produced += 1
