from typing import List, Optional, Set, Tuple

from .definitions import rules, MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL
from .lib.log import debug, warning, exception
from .lib.nofloat import PRECISION, square_of_distance, int_cos_1000, int_sin_1000, int_angle, int_distance
from .worldaction import Action, AttackAction, MoveAction, MoveXYAction
from .worldentity import Entity
from .worldorders import ORDERS_DICT, GoOrder, RallyingPointOrder, BuildPhaseTwoOrder, UpgradeToOrder
from .worldresource import Corpse, Deposit
from .worldroom import Square

DISTANCE_MARGIN = 175 # millimeters

def ground_or_air(t):
    return "ground" if t == "water" else t

    
class Creature(Entity):

    type_name: Optional[str] = None
    is_a_unit = False
    is_a_building = False

    def get_action_target(self):
        if self.action:
            return self.action.target

    def set_action_target(self, value):
        if isinstance(value, tuple):
            self.action = MoveXYAction(self, value)
        elif type(value).__name__ == "ZoomTarget":
            self.action = MoveXYAction(self, (value.x, value.y))
        elif self.is_an_enemy(value):
            self.action = AttackAction(self, value)
        elif value is not None:
            self.action = MoveAction(self, value)
        else:
            self.action = Action(self, value)

    action_target = property(get_action_target, set_action_target)

    hp_max = 0
    hp_regen = 0
    mana_max = 0
    mana_start = 0
    mana_regen = 0
    walked: List[Tuple[Optional[Square], int, int, int]] = []

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    time_cost = 0
    food_cost = 0
    food_provided = 0
    ai_mode: Optional[str] = None
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

    basic_abilities: Set[str] = set()

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

    rallying_point = None

    corpse = 1
    decay = 0

    presence = 1

    count_limit = 0
    group = None

    def next_free_number(self):
        numbers = [u.number for u in self.player.units if u.type_name == self.type_name and u is not self]
        n = 1
        while n in numbers:
            n += 1
        return n

    def set_player(self, player):
        # stop current action
        self.stop()
        self.cancel_all_orders(unpay=False)
        # remove from previous player
        if self.player is not None:
            self.player.units.remove(self)
            self.player.food -= self.food_provided
            self.player.used_food -= self.food_cost
        # add to new player
        self.player = player
        if player is not None:
            self.number = self.next_free_number()
            player.units.append(self)
            self.player.food += self.food_provided
            self.player.used_food += self.food_cost
            self.upgrade_to_player_level()
            # player units must stop attacking the "not hostile anymore" unit
            for u in player.units:
                if u.action_target is self:
                    u.stop()
            # note: updating perception so quickly shouldn't be necessary
            # (now that perception isn't strictly limited to squares)
            # It doesn't take time though.
            for p in player.allied_vision:
                p.perception.add(self) # necessary for example for new building sites
        # if transporting units, set player for them too
        for o in self.objects:
            o.set_player(player)

    def __init__(self, prototype, player, place, x, y, o=90):
        if prototype is not None:
            prototype.init_dict(self)
        self.orders = []

        # attributes required by transports and shelters (inside)
        self.objects = []
        self.world = place.world
        self.neighbors = []
        self.title = []

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
            self.minimal_damage = int(.17 * PRECISION)

        # move to initial place
        Entity.__init__(self, place, x, y, o)
        self.position_to_hold = place # defend the creation place

        if self.decay:
            self.time_limit = self.world.time + self.decay

    def upgrade_to_player_level(self):
        for upg in self.can_use:
            if upg in self.player.upgrades:
                self.world.unit_class(upg).upgrade_unit_to_player_level(self)

    @property
    def upgrades(self):
        return [u for u in self.can_use if u in self.player.upgrades]

    # method required by transports and shelters (inside)
    def contains_enemy(self, player):
        return False

    @property
    def height(self):
        if self.airground_type == "air":
            return 2
        else:
            return self.place.height + self.bonus_height

    def nearest_water(self):
        places = [sq for sq in self.place.strict_neighbors if sq.is_water]
        if places:
            return min(places, key=lambda sq: square_of_distance(sq.x, sq.y, self.x, self.y))

    def get_observed_squares(self, strict=False, partial=False):
        if self.is_inside or self.place is None:
            return []
        result = [self.place]
        if partial:
            return result + self.place.neighbors
        if strict and self.sight_range < self.world.square_width:
            return result
        for sq in self.place.neighbors:
            if self.height > sq.height \
            or self.height == sq.height and self._can_go(sq):
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
        d = self.actual_speed * VIRTUAL_TIME_INTERVAL // 1000
        if rotation == 0:
            d = min(d, target_d) # stop before colliding target
        a = self.o + rotation
        x = self.x + d * int_cos_1000(a) // 1000
        y = self.y + d * int_sin_1000(a) // 1000
        return x, y

    def _heuristic_value(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        return abs(rotation) + self._already_walked(x, y) * 200

    def _can_go(self, new_place, ignore_blockers=False):
        if new_place is None: return False # out of the map
        if self.airground_type != "ground":
            return True
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

    def _mark_the_dead_end(self) -> None:
        self.walked.append((self.place, self.x, self.y, 5))

    def _must_hold(self):
        return (not self.orders or self.orders[0].is_complete) and \
           self.position_to_hold is not None and \
           self.position_to_hold.contains(self.x, self.y)

    def _must_not_go_to(self, x, y):
        return self._must_hold() and not self.position_to_hold.contains(x, y)

    def _try(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        new_place = self.world.get_place_from_xy(x, y)
        if self._must_not_go_to(x, y):
            return False
        if self._can_go(new_place) and not self.would_collide_if(x, y):
            if abs(rotation) >= 90: self._mark_the_dead_end()
            self.move_to(new_place, x, y, self.o + rotation)
            self.unblock()
            return True

    _rotations = None
    _smooth_rotations = None

    def _reach(self, target_d):
        if self._smooth_rotations: # "smooth rotation" mode
            rotation = self._smooth_rotations.pop(0)
            if self._try(rotation, target_d) or self._try(-rotation, target_d):
                self._smooth_rotations = []
        else:
            if not self._rotations:
                # update memory of dead ends
                self.walked = [x[0:3] + (x[3] - 1, ) for x in self.walked if x[3] > 1]
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
                self._smooth_rotations = list(range(1, 180, 1))
                self.walked = []
                self._mark_the_dead_end()
                self.notify("collision")

    # hold

    def deploy(self):
        if type(self.position_to_hold).__name__ == "ZoomTarget":
            self.action_target = self.position_to_hold
        elif self.player.smart_units:
            self.action_target = self.player.get_safest_subsquare(self.place)
        else:
            self.action_target = self.place.x, self.place.y

    def is_in_position(self, target):
        if self.place is target: return True
        if type(target).__name__ == "ZoomTarget":
            return target.contains(self.x, self.y)

    def hold(self, target):
        self.position_to_hold = target
        self.deploy()

    # reach

    @property
    def is_melee(self):
        return self.range <= 2 * PRECISION

    def _near_enough_to_aim(self, target):
        # Melee units shouldn't attack units on the other side of a wall.
        if self.is_melee and not self._can_go(target.place) and not target.blocked_exit:
            return False
        if self.minimal_range and square_of_distance(self.x, self.y, target.x, target.y) < self.minimal_range * self.minimal_range:
            return False
        range = self.range
        if self.is_ballistic and self.height > target.height:
            # each height difference has a bonus of 1
            bonus = (self.height - target.height) * PRECISION * 1
            range += bonus
        d = max(self.radius + DISTANCE_MARGIN, range) + target.radius
        return square_of_distance(self.x, self.y, target.x, target.y) < d * d

    def _near_enough(self, target):
        # note: always returns False if the target is a square
        if target.place is self.place:
            d = self.radius + target.radius + DISTANCE_MARGIN
            return square_of_distance(self.x, self.y, target.x, target.y) < d * d

    def _collision_range(self, other):
        if self.collision and other.collision and \
           other.airground_type == self.airground_type:
            return self.radius + other.radius
        else:
            return 0

    def action_reach_and_stop(self):
        target = self.action_target
        if not self._near_enough(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y) # turn toward the goal
            self._reach(d - self._collision_range(target))
        else:
            self.walked = []
            self.target = None

    def action_reach_and_aim(self):
        target = self.action_target
        if not self._near_enough_to_aim(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y) # turn toward the goal
            self._reach(d - self._collision_range(target))
        else:
            self.walked = []
            self.aim(target)

    def go_to_xy(self, x, y):
        d = int_distance(self.x, self.y, x, y)
        if d > self.radius:
            self.o = int_angle(self.x, self.y, x, y) # turn toward the goal
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
        assert isinstance(self.hp, int)
        assert isinstance(self.mana, int)
        assert isinstance(self.x, int)
        assert isinstance(self.y, int)
        assert isinstance(self.o, int)

        self.is_moving = False

        if self.is_inside or self.player is None:
            return

        if self.heal_level:
            self.heal_nearby_units()
        if self.harm_level:
            self.harm_nearby_units()

        if self.action:
            self.action.update()

        if self.has_imperative_orders():
            # warning: completing UpgradeToOrder deletes the object
            self._execute_orders()
        else:
            self.decide()
            if not self._is_attacking() and self.orders:
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

    #

    def _raise_subsquare_threat(self, delta):
        subsquare = self.world.get_subsquare_id_from_xy(self.x, self.y)
        for p in self.player.allied_vision:
            if p in self.player.allied:
                p.raise_threat(subsquare, delta)

    def receive_hit(self, damage, attacker, notify=True):
        if self.player is not None:
            self.player.observe(attacker)
            self._raise_subsquare_threat(damage)
        else:
            warning("player is None in receive_hit()")
        self.hp -= damage
        if self.hp < 0:
            self.die(attacker)
        else:
            if notify:
                self.notify("wounded,%s,%s,%s" %
                            (attacker.type_name, attacker.id, attacker.damage_level))
            self.player.on_unit_attacked(self, attacker)

    def delete(self):
        Entity.delete(self)
        self.set_player(None)

    def die(self, attacker):
        # remove transported units
        for o in self.objects[:]:
            o.move_to(self.place, self.x, self.y)
            if o.place is self: # not enough space
                o.collision = 0
                o.move_to(self.place, self.x, self.y)
            if self.airground_type != "ground":
                o.die(attacker)
        self.notify("death")
        if attacker is not None:
            self.notify("death_by,%s" % attacker.id)
            self.player.on_unit_attacked(self, attacker)
        self.delete()

    heal_level = 0

    def heal_nearby_units(self):
        # level 1 of healing: 1 hp every 7.5 seconds
        hp = self.heal_level * PRECISION // 25
        allies = self.player.allied
        units = self.world.get_objects2(self.x, self.y, 6 * PRECISION,
                filter=lambda x: x.is_healable and x.hp < x.hp_max,
                players=allies)
        for u in units:
            u.hp = min(u.hp_max, u.hp + hp)

    harm_target_type = ()

    def _can_harm(self, other):
        return self.world.can_harm(self.type_name, other.type_name)

    def harm_nearby_units(self):
        # level 1: 1 hp every 7.5 seconds
        hp = self.harm_level * PRECISION // 25
        units = self.world.get_objects2(self.x, self.y, 6 * PRECISION,
                filter=lambda x: x.is_vulnerable and self._can_harm(x))
        for u in units:
            u.receive_hit(hp, self, notify=False)

    def is_an_enemy(self, c):
        if isinstance(c, Creature):
            if self.has_imperative_orders() and \
               self.orders[0].__class__ == GoOrder and \
               self.orders[0].target is c:
                return True
            else:
                return self.player.player_is_an_enemy(c.player)
        else:
            return False

    def can_attack_if_in_range(self, other):
        if self.is_inside or not self.damage:
            return False
        if other not in self.player.perception:
            return False
        if other is None \
           or other.place is None \
           or getattr(other, "hp", 0) < 0 \
           or ground_or_air(getattr(other, "airground_type", None)) not in self.target_types:
            return False
        if not other.is_vulnerable:
            return False
        return True

    def can_attack(self, other): # without moving to another square
        if not self.can_attack_if_in_range(other):
            return False
        if self.range and other.place is self.place:
            return True
        return self._near_enough_to_aim(other)

    def _choose_enemy(self, place):
        known = self.player.known_enemies(place)
        reachable_enemies = [x for x in known if self.can_attack(x)]
        if reachable_enemies:
            reachable_enemies.sort(key=lambda x: (- x.menace, square_of_distance(self.x, self.y, x.x, x.y), x.id))
            self.action = AttackAction(self, reachable_enemies[0])
            return True

    def flee(self):
        if self._previous_square is not None \
           and self.player.balance(self._previous_square) > .5:
            if self.action_target != self.next_stage(self._previous_square):
                self.notify("flee")
                self.take_order(["go", self._previous_square.id], imperative=True)
            
    def decide(self):
        if (self.player.smart_units or self.ai_mode == "defensive") \
           and self.speed > 0 and not self._must_hold() \
           and self.player.balance(self.place, self._previous_square) < .5:
            self.flee()
            return
        if not self.damage or getattr(self.action_target, "menace", 0):
            return
        if self._choose_enemy(self.place):
            return
        for p in self.place.neighbors:
            if self._choose_enemy(p):
                break

    # attack

    def hit(self, target):
        damage = max(self.minimal_damage, self.damage - target.armor)
        target.receive_hit(damage, self)

    def _hit_or_miss(self, target):
        if self.has_hit(target):
            self.hit(target)
        else:
            target.notify("missed")

    def splash_aim(self, target):
        damage_radius_2 = self.damage_radius * self.damage_radius
        for o in target.place.objects[:]:
            if not self.is_an_enemy(o) and o is not target:
                pass  # no friendly fire (unless o is the target)
            elif isinstance(o, Creature) \
               and square_of_distance(o.x, o.y, target.x, target.y) <= damage_radius_2 \
               and self.can_attack_if_in_range(o):
                self._hit_or_miss(o)

    def chance_to_hit(self, target):
        high_ground = not self.place.high_ground and target.place.high_ground \
                      and target.airground_type == "ground" \
                      and not self.is_melee \
                      and self.height < target.height
        result = 50 if high_ground else 100
        if not self.is_melee:
            result = result * (100 - target.place.terrain_cover[0 if target.airground_type != "air" else 1]) // 100
        return result

    def has_hit(self, target):
        chance = self.chance_to_hit(target)
        return True if chance == 100 else self.world.random.randint(1, 100) <= chance

    def aim(self, target):
        if self.can_attack(target) and self.place.world.time >= self.next_attack_time:
            self.next_attack_time = self.place.world.time + self.cooldown
            self.notify("launch_attack")
            if self.splash:
                self.splash_aim(target)
            else:
                self._hit_or_miss(target)

    # orders

    def take_order(self, o, forget_previous=True, imperative=False, order_id=None):
        # an imperative "go" order on a unit is an "attack" order
        # note: this could be done by the user interface
        if imperative and o[0] == "go":
            target = self.player.get_object_by_id(o[1])
            if getattr(target, "player", None) is not None:
                o[0] = "attack"
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
            if self.player.available_food < self.world.food_limit:
                return "not_enough_food"
            else:
                return "population_limit_reached"

    def cancel_all_orders(self, unpay=True):
        while self.orders:
            self.orders.pop().cancel(unpay)

    def must_build(self, order):
        for o in self.orders:
            if o == order:
                return True

    def _put_building_site(self, type, target):
        # if the target is a memory, get the true object instead
        if getattr(target, "is_memory", False): target = target.initial_model
        # remember before deletion
        place, x, y, _id = target.place, target.x, target.y, target.id
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
                if unit.orders[n] == order:
                    # help the first worker
                    unit.orders[n] = BuildPhaseTwoOrder(unit, [site.id])
                    unit.orders[n].on_queued()
        self.orders[0] = BuildPhaseTwoOrder(self, [site.id])
        self.orders[0].on_queued()

    def _delta(self, total, percentage):
        # Initial formula (reordered for a better precision):
        # delta = (percentage / 100) * total / (self.time_cost / VIRTUAL_TIME_INTERVAL)
        try:
            delta = int(total * percentage * VIRTUAL_TIME_INTERVAL // self.time_cost // 100)
        except ZeroDivisionError:
            delta = int(total * percentage * VIRTUAL_TIME_INTERVAL // 100)
        if delta == 0 and total != 0:
            warning("insufficient precision (delta: %s total: %s)", delta, total)
        return delta

    @property
    def hp_delta(self):
        return self._delta(self.hp_max, 70)

    @property
    def repair_cost(self): # per turn
        return (self._delta(c, 30) for c in self.cost)

    def be_built(self, actor):
        if self.hp < self.hp_max:
            result = actor.check_if_enough_resources(self.repair_cost)
            if result is not None:
                actor.notify("order_impossible,%s" % result)
                actor.orders[0].mark_as_complete()
            else:
                actor.player.pay(self.repair_cost)
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

    def load_all(self, place=None):
        if place is None:
            place = self.place
        for u in sorted(self.player.units, key=lambda x: x.transport_volume, reverse=True):
            if u.place is place and self.have_enough_space(u):
                self.load(u)

    def unload_all(self, place=None):
        if place is None:
            place = self.place
            x = self.x
            y = self.y
        else:
            x = place.x
            y = place.y
        for o in self.objects[:]:
            o.move_to(place, x, y)
            o.notify("exit")

    #

    def stop(self):
        self.action_target = None
        self.position_to_hold = None

    @property
    def is_idle(self):
        return self.action_target is None


class Unit(Creature):

    food_cost = 1

    is_cloakable = True
    is_a_gate = True
    is_a_unit = True

    def __init__(self, player, place, x, y, o=90):
        Creature.__init__(self, player, place, x, y, o)
        self.player.nb_units_produced += 1

    def die(self, attacker=None):
        self.player.nb_units_lost += 1
        if attacker:
            attacker.player.nb_units_killed += 1
        if self.corpse:
            Corpse(self)
        Creature.die(self, attacker)

    @property
    def basic_abilities(self):
        for o in self.orders:
            if isinstance(o, UpgradeToOrder):
                return set()
        return self._basic_abilities

    # actions

    def next_square(self, target, avoid=False):
        next_stage = self.next_stage(target, avoid=avoid)
        try:
            return next_stage.other_side.place
        except AttributeError:
            return next_stage

    def next_stage(self, target, avoid=False):
        if target is None or target.place is None:
            return None
        if not hasattr(target, "exits"): # target is not a square
            if self.place == target.place:
                return target
            place = target.place
        else: # target is a square
            if self.place == target:
                return None
            place = target
        if not hasattr(place, "exits"): # not a square
            return None
        return self.place.shortest_path_to(place, player=self.player, plane=self.airground_type, avoid=avoid)

    def start_moving_to(self, target, avoid=False):
        # note: it can be an attack
        # note: several calls might be necessary
        self.action_target = self.next_stage(target, avoid=avoid)

    def _next_stage_to_enemy(self):
        for e in self.place.exits:
            if e.other_side.place.contains_enemy(self.player):
                return e
        return self.next_stage(self.world.random.choice(self.world.squares))

    def start_moving_to_enemy(self):
        if self.place.contains_enemy(self.player):
            self._choose_enemy(self.place)
        else:
            self.action_target = self._next_stage_to_enemy()

##    def _should_explore_now(self, place):
##        return place not in self._already_explored and \
##            not self.player.is_very_dangerous(place)
##
##    def __auto_explore(self):
##        self._already_explored.update(self.player.observed_squares)
##        if self.is_idle:
##            self._places_to_explore = [x for x in self._places_to_explore
##                                       if x not in self._already_explored]
##            if self._places_to_explore:
##                place = self._places_to_explore[0]
##                self.start_moving_to(place, avoid=True)
##                if self.is_idle: # place is inaccessible
##                    self._places_to_explore.remove(place)
##            if not self._places_to_explore:
##                self._places_to_explore = [p for p in self.world.squares
##                                           if self._should_explore_now(p)]
##                self.world.random.shuffle(self._places_to_explore)
##                self._already_explored = set()
##        elif self.player.is_very_dangerous(self.action_target):
##            self.stop()

    def auto_explore(self):
        if not self.action_target:
            def should_explore_now(place):
                return place not in self.player._already_explored and \
                    not self.player.is_very_dangerous(place)
            self.player._already_explored.update([o.place for o in self.player.perception])
            self.player._places_to_explore = [x for x in self.player._places_to_explore if x not in self.player._already_explored]
            if not self.player._places_to_explore:
                self.player._places_to_explore = [p for p in self.world.squares if should_explore_now(p)]
                self.world.random.shuffle(self.player._places_to_explore)
            for place in self.player._places_to_explore[:]:
                self.action_target = self.next_stage(place, avoid=True)
                if self.action_target is not None:
                    return
                else:
                    self.player._places_to_explore.remove(place)
            self.player._already_explored = {o.place for o in self.player.perception}
        elif self.player.is_very_dangerous(self.action_target):
            if not self.player.is_very_dangerous(self.place):
                self.action_target = None
        elif self.player.is_very_dangerous(self.place):
            # assertion: self._previous_square is not None
            if not self.player.is_very_dangerous(self._previous_square):
                self.start_moving_to(self._previous_square)

    def move_on_border(self, e):
        self.move_to(e.place, e.x, e.y)

    def block(self, e):
        if not self.blocked_exit:
            self.blocked_exit = e
            e.add_blocker(self)


class Worker(Unit):

    ai_mode = "defensive"
    auto_gather = True
    auto_repair = True
    can_switch_ai_mode = True
    _basic_abilities = {"go", "attack", "gather", "repair", "block", "join_group"}
    is_teleportable = True
    cargo = None # gathered resource

    def decide(self):
        Unit.decide(self)
        if self.player.__class__.__name__ != "Human":
            return
        if self.orders and self.orders[0].keyword != "gather":
            return
        if self.auto_repair:
            for p in self.player.allied:
                for u in p.units:
                    if u.place is self.place and u.is_repairable and u.hp < u.hp_max \
                       and not isinstance(u, BuildingSite) \
                       and self.check_if_enough_resources(u.repair_cost) is None:
                        self.take_order(["repair", u.id])
                        return
        if self.orders:
            return
        if self.auto_gather:
            local_warehouses_resource_types = set()
            for w in self.place.objects:
                if w.player in self.player.allied:
                    local_warehouses_resource_types.update(w.storable_resource_types)
            if local_warehouses_resource_types:
                deposits = [o for o in self.place.objects if isinstance(o, Deposit)
                            and o.resource_type in local_warehouses_resource_types]
                if deposits:
                    if self.cargo and self.cargo[0] not in local_warehouses_resource_types:
                        self.cargo = None
                    o = self.world.random.choice(deposits)
                    self.take_order(["gather", o.id])


class Soldier(Unit):

    ai_mode = "offensive"
    can_switch_ai_mode = True
    _basic_abilities = {"go", "attack", "patrol", "block", "join_group"}
    is_teleportable = True


class Effect(Unit):
    collision = 0
    corpse = 0
    food_cost = 0
    is_vulnerable = False
    presence = 0
    _basic_abilities: Set[str] = set()

    def die(self, attacker=None):
        self.delete()


class _Building(Creature):

    ai_mode = "offensive"
    can_switch_ai_mode = False # never flee

    is_repairable = True # or buildable (in the case of a BuildingSite)
    is_healable = False
    is_a_building = True

    transport_volume = 99

    corpse = 0

    def __init__(self, prototype, player, square, x=0, y=0):
        Creature.__init__(self, prototype, player, square, x, y)

    def die(self, attacker=None):
        self.player.nb_buildings_lost += 1
        if attacker:
            attacker.player.nb_buildings_killed += 1
        place, x, y = self.place, self.x, self.y
        Creature.die(self, attacker)
        if self.building_land:
            self.building_land.move_to(place, x, y)


class BuildingSite(_Building):

    type_name = "buildingsite"
    basic_abilities = {"cancel_building"}

    def __init__(self, player, place, x, y, building_type):
        player.pay(building_type.cost)
        _Building.__init__(self, None, player, place, x, y)
        self.type = building_type
        self.hp_max = building_type.hp_max
        self._starting_hp = building_type.hp_max * 5 // 100
        self.hp = self._starting_hp
        self.timer = building_type.time_cost // VIRTUAL_TIME_INTERVAL
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
    def is_buildable_near_water_only(self):
        return self.type.is_buildable_near_water_only

    @property
    def is_a_gate(self):
        return self.type.is_a_gate

    @property
    def time_cost(self):
        return self.type.time_cost

    @property
    def hp_delta(self):
        return self._delta(self.hp_max - self._starting_hp, 100)

    def be_built(self, actor):
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
    is_buildable_near_water_only = False
    provides_survival = True

    def __init__(self, prototype, player, place, x, y):
        _Building.__init__(self, prototype, player, place, x, y)
        self.player.nb_buildings_produced += 1
