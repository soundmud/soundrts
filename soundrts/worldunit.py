import worldrandom

from commun import *
from constants import *
from worldentity import *
from worldresource import *
from worldroom import *


ORDERS_QUEUE_LIMIT = 10
MAX_NB_OF_RESOURCE_TYPES = 10


class Creature(Entity):

    type_name = None
    
    action_type = None
    action_target = None

    def getcible(self):
        return self.action_target

    def setcible(self, value):
        if isinstance(value, tuple):
            self.action_type = "move"
            self._reach_xy_timer = 15 # 5 seconds # XXXXXXXX not beautiful
        elif self.is_an_enemy(value):
            self.action_type = "attack"
        elif value is not None:
            self.action_type = "move" # "use" ?
        else:
            self.action_type = None
        self.action_target = value

    cible = property(getcible, setcible)

    hp_max = 0
    mana_max = 0
    mana_regen = 0
    walked = []

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    time_cost = 0
    food_cost = 0
    food_provided = 0
    need = None
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

    basic_abilities = []

    is_vulnerable = True
    is_healable = True

    sight_range = 0

    damage_radius = 0
    target_types = ["ground"]
    range = None
    is_ballistic = 0
    special_range = 0
    cooldown = None
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

    def next_free_number(self):
        numbers = [u.number for u in self.player.units if u.type_name == self.type_name and u is not self]
        n = 1
        while n in numbers:
            n += 1
        return n

    def set_player(self, player):
        # stop current action
        self.cible = None
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
                if u.cible is self:
                    u.cible = None
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
        self.mana = self.mana_max

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
            return self.place.height

    def get_observed_squares(self):
        if self.is_inside or self.place is None:
            return []
        result = [self.place]
        for sq in self.place.neighbours:
            if self.height > sq.height or self.sight_range == 1 and self.height >= sq.height:
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
        if hasattr(o, "mode") and o.mode == "construire":
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

    def _future_coords(self, steer, dmax):
        # XXX: assertion: self.o points to the target
        if steer == 0:
            d = min(self._d, dmax) # stop before colliding target
        else:
            d = self._d
        a = self.o + steer
        x = self.x + d * int_cos_1000(a) / 1000
        y = self.y + d * int_sin_1000(a) / 1000
        return x, y

    def _heuristic_value(self, steer, dmax):
        x, y = self._future_coords(steer, dmax)
        return abs(steer) + self._already_walked(x, y) * 200

    def _try(self, steer, dmax):
        x, y = self._future_coords(steer, dmax)
        if not self.place.dans_le_mur(x, y) and not self.would_collide_if(x, y):
            if abs(steer) >= 90:
                self.walked.append([self.place, self.x, self.y, 5]) # mark the dead end
            self.move_to(self.place, x, y, self.o + steer)
            return True
        return False

    _steers = None
    _smooth_steers = None

    def _reach(self, dmax):
        self._d = self.speed * VIRTUAL_TIME_INTERVAL / 1000 # used by _future_coords and _heuristic_value
        if self._smooth_steers:
            # "smooth steering" mode
            steer = self._smooth_steers.pop(0)
            if self._try(steer, dmax) or self._try(-steer, dmax):
                self._smooth_steers = []
        else:
            if not self._steers:
                # update memory
                self.walked = [x[0:3] + [x[3] - 1] for x in self.walked if x[3] > 1]
                # "go straight" mode
                if not self.walked and self._try(0, dmax): return
                # enter "steering mode"
                self._steers = [(self._heuristic_value(x, dmax), x) for x in
                          (0, 45, -45, 90, -90, 135, -135, 180)]
                self._steers.sort()
            # "steering" mode
            for _ in range(min(4, len(self._steers))):
                _, steer = self._steers.pop(0)
                if self._try(steer, dmax):
                    self._steers = []
                    return
            if not self._steers:
                # enter "smooth steering mode"
                self._smooth_steers = range(1, 180, 1)
                self.walked = []
                self.walked.append([self.place, self.x, self.y, 5]) # mark the dead end
                self.notify("collision")

    # go center

    def action_reach_xy(self):
        x, y = self.cible
        d = int_distance(self.x, self.y, x, y)
        if self._reach_xy_timer > 0 and d > self.radius:
            # execute action
            self.o = int_angle(self.x, self.y, x, y) # turn toward the goal
            self._reach(d)
            self._reach_xy_timer -= 1
        else:
            self.action_complete()

    def _go_center(self):
        self.cible = (self.place.x, self.place.y)

    def _near_enough_to_use(self, target):
        if self.is_an_enemy(target):
            if self.range and target.place is self.place:
                d = target.use_range(self)
                return square_of_distance(self.x, self.y, target.x, target.y) < d * d
            elif self.is_ballistic or self.special_range:
                return self.can_attack(target)
        elif target.place is self.place:
            d = target.use_range(self)
            return square_of_distance(self.x, self.y, target.x, target.y) < d * d

    def be_used_by(self, actor):
        if actor.is_an_enemy(self):
            actor.aim(self)

    # reach and use

    def action_reach_and_use(self):
        target = self.cible
        if not self._near_enough_to_use(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y) # turn toward the goal
            self._reach(d - target.collision_range(self))
        else:
            self.walked = []
            target.be_used_by(self)

    # fly to

    def action_fly_to_remote_target(self):
        def get_place_from_xy(x, y):
            for z in self.place.world.squares:
                if z.contains_xy(x, y):
                    return z
        dmax = int_distance(self.x, self.y, self.cible.x, self.cible.y)
        self.o = int_angle(self.x, self.y, self.cible.x, self.cible.y) # turn toward the goal
        self._d = self.speed * VIRTUAL_TIME_INTERVAL / 1000 # used by _future_coords and _heuristic_value
        x, y = self._future_coords(0, dmax)
        if self.place.dans_le_mur(x, y):
            try:
                new_place = get_place_from_xy(x, y)
                self.move_to(new_place, x, y, self.o)
            except:
                exception("problem when flying to a new square")
        else:
            self.move_to(self.place, x, y)

    # update

    def has_imperative_orders(self):
        return self.orders and self.orders[0].is_imperative

    def _execute_orders(self):
        queue = self.orders
        if queue[0].is_complete or queue[0].is_impossible:
            queue.pop(0)
        else:
            queue[0].update()

    def action_complete(self):
        self.walked = []
        self.cible = None
        self._flee_or_fight_if_enemy()

    def act_move(self):
        if isinstance(self.action_target, tuple):
            self.action_reach_xy()
        elif getattr(self.cible, "place", None) is self.place:
            self.action_reach_and_use()
        elif self.airground_type == "air":
            self.action_fly_to_remote_target()
        else:
            self.action_complete()

    def act_attack(self): # without moving to another square
        if self.range and self.cible in self.place.objects:
            self.action_reach_and_use()
        elif self.is_ballistic and self.place.is_near(getattr(self.cible, "place", None)) \
             and self.height > self.cible.height:
            self.aim(self.cible)
        elif self.special_range and self.place.is_near(getattr(self.cible, "place", None)):
            self.aim(self.cible)
        else:
            self.action_complete()

    def update(self):
        assert isinstance(self.hp, int)
        assert isinstance(self.mana, int)
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
        if self.action_type:
            getattr(self, "act_" + self.action_type)()
        # order level (warning: completing UpgradeToOrder deletes the object)
        if self.has_imperative_orders():
            self._execute_orders()
        else:
            # catapult try to find enemy # XXXXX later: do this in triggers
            if self.special_range and self.action_type != "attack": # XXXX if self.special_range or self.range?
                self.choose_enemy()
            if self.is_ballistic and self.height == 1 and self.action_type != "attack":
                self.choose_enemy()
            # execute orders if the unit is not fighting (targetting an enemy)
            if self.orders and self.action_type != "attack":
#            # experimental: execute orders if no current action
#            if self.orders and not self.action_type:
                self._execute_orders()

    # slow update

    def regenerate(self):
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

    def can_attack(self, other): # without moving to another square
        # assert other in self.player.perception # XXX false
        # assert not self.is_inside # XXX not sure

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
        if self.range and other.place is self.place:
            return True
        if self.place.is_near(other.place):
            if self.special_range:
                return True
            if self.is_ballistic and self.height > other.height:
                return True

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
            self.cible = reachable_enemies[0] # attack nearest
            self.notify("attack") # XXX move this into set_cible()?
            return True
##        else:
##            for u in enemy_units:
##                if u.can_attack(self) and not u._can_be_reached_by(self.player):
##                    self.flee()
##                    return

    def choose_enemy(self, someone=None):
        if self.has_imperative_orders():
            return
        if not self.damage:
            return
        if getattr(self.cible, "menace", 0):
            return
        if someone is not None and self.can_attack(someone):
            self.cible = someone
            self.notify("attack") # XXX move this into set_cible()?
            return
        if self.range and self._choose_enemy(self.place):
            return
        if self.is_ballistic:
            for p in self.place.neighbours:
                if self.height > p.height and self._choose_enemy(p):
                    break
        if self.special_range:
            for p in self.place.neighbours:
                if self._choose_enemy(p):
                    break

    #

    def on_wounded(self, attacker, notify):
        if self.player is not None:
            self.player.observe(attacker)
        # Why level 0 only for "wounded,type,0":
        # maybe a single sound would be better: simpler,
        # allowing more levels of upgrade, and examining
        # unit upgrades in the stats is better?
        if notify:
            self.notify("wounded,%s,%s,%s" % (attacker.type_name, attacker.id, 0))
        # react only if this is an external attack
        if self.player is not attacker.player and \
           attacker.is_vulnerable and \
           attacker in self.player.perception:
            self.player.on_unit_attacked(self, attacker)
            for u in self.player.units:
                if u.place == self.place:
                    u.on_friend_unit_attacked(attacker)

    def on_friend_unit_attacked(self, attacker):
        if self.has_imperative_orders():
            return
        if not self.is_fleeing and \
           (getattr(self.cible, "menace", 0) < attacker.menace) and \
             self.can_attack(attacker) and \
             self.place == attacker.place:
            self.cible = attacker

    def react_death(self, creature):
        if self.cible == creature:
            self.cible = None
            self.choose_enemy()
            self.player.update_attack_squares(self) # XXXXXXX ?
        elif self.place == creature.place:
            self._flee_or_fight()

    def react_go_through(self, someone, unused_door):
        if someone == self.cible:
            self.cible = None
            self.choose_enemy() # choose another enemy

    def _flee_or_fight_if_enemy(self):
        if self.place.contains_enemy(self.player):
            self._flee_or_fight()

    def _flee_or_fight(self, someone=None):
        if self.has_imperative_orders():
            return
        if self.is_fleeing:
            return
        if self.ai_mode == "defensive":
            if self.place.balance(self.player) >= 0:
                self.choose_enemy(someone)
            else:
                self.flee(someone)
        elif self.ai_mode == "offensive":
            self.choose_enemy(someone)

    def react_arrives(self, someone, door=None):
        if self.place is someone.place and not self.is_fleeing:
            self._flee_or_fight(someone)

    def door_menace(self, door):
        if door in self.player.enemy_doors:
            return 1
        else:
            return 0

    def flee(self, someone=None):
        self.notify("flee")
        self.player.on_unit_flee(self)
        self.orders = []
        if someone is None:
            exits = [[(square_of_distance(e.x, e.y, self.x, self.y), e.id), e] for e in self.place.exits]
        else:
            exits = [[(self.door_menace(e), - square_of_distance(e.x, e.y, someone.x, someone.y), e.id), e] for e in self.place.exits]
        exits.sort()
        if len(exits) > 0:
            self.cible = exits[0][1]
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
        damage = max(0, self.damage - target.armor)
        target.receive_hit(damage, self)

    def splash_aim(self, target):
        damage_radius_2 = self.damage_radius * self.damage_radius
        for o in target.place.objects[:]:
            if not self.is_an_enemy(o):
                pass  # no friendly fire
            elif isinstance(o, Creature) \
               and square_of_distance(o.x, o.y, target.x, target.y) <= damage_radius_2 \
               and self.can_attack(o):
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
        if not type.is_buildable_anywhere:
            target.delete() # remove the meadow replaced by the building
        site = BuildingSite(self.player, place, x, y, type)

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
            return self.place.shortest_path_to(target.place)
        else: # target is a square
            if self.place == target:
                return None
            return self.place.shortest_path_to(target)

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
        if not self.cible:
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
                        self.cible = self.next_stage(place)
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


class Worker(Unit):

    value = 0 # not 0.1 to avoid "combat 1 against 10" (misleading) XXX
    ai_mode = "defensive"
    can_switch_ai_mode = True
    _basic_abilities = ["go", "gather", "repair"]


class Soldier(Unit):

    ai_mode = "offensive"
    can_switch_ai_mode = True
    _basic_abilities = ["go", "patrol"]


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
        if not self.is_buildable_anywhere:
            Meadow(place, x, y)

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
            self.delete()
            building = self.type(player, place, x, y)
            building.hp = self.type.hp_max - self.damage_during_construction
            building.notify("complete")

    @property
    def is_fully_repaired(self):
        return False


class Building(_Building):

    is_buildable_anywhere = False

    def __init__(self, prototype, player, place, x, y):
        _Building.__init__(self, prototype, player, place, x, y)
        self.player.nb_buildings_produced += 1


class Order(object):

    target = None
    type = None
    is_impossible = False
    is_complete = False
    is_imperative = False
    cancel_order = "stop"
    never_forget_previous = False
    unit_menu_attribute = None
    can_be_followed = True

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    food_cost = 0

    is_deferred = False
    nb_args = 0

    def __init__(self, unit, args):
        self.unit = unit
        self.args = args

    def __eq__(self, other): return False
    def __ne__(self, other): return not self.__eq__(other)

    __first_update = True

    def execute(self): pass

    def update(self):
        if self.__first_update:
            self.unit.cible = None
            self.__first_update = False
        self.execute()

    @property
    def player(self):
        return self.unit.player

    def cancel(self, unpay=True): pass

    def mark_as_impossible(self, reason=None):
        self.is_impossible = True
        n = "order_impossible"
        if reason is not None:
            n += "," + reason
        self.unit.notify(n)

    def mark_as_complete(self):
        self.is_complete = True

    def update_target(self):
        t = self.target
        p = self.unit.player
        if t is not None and \
           t not in p.world.squares and \
           t not in p.perception and \
           t not in p.memory:
            self.target = p.get_object_by_id(t.id)

    def move_to_or_fail(self, target):
        if self.unit.speed == 0:
            self.mark_as_impossible()
            return
        self.unit.cible = self.unit.next_stage(target)
        if self.unit.cible is None: # target is unreachable
            self.mark_as_impossible()
            self.unit._go_center() # do not block the path

    def immediate_action(self):
        if len(self.unit.orders) >= ORDERS_QUEUE_LIMIT:
            self.unit.notify("order_impossible,the_queue_is_full")
        # if the queue is empty and food is required and not enough food is available then don't queue
        elif not self.unit.orders and self.food_cost != 0 and self.unit.player.available_food < self.unit.player.used_food + self.food_cost:
            self.unit.notify("order_impossible,not_enough_food")
        else:
            self.unit.orders.append(self)
            self.on_queued()

    @classmethod
    def menu(cls, unit, strict=False):
        if strict:
            condition = cls.is_allowed
        else:
            condition = cls.is_almost_allowed
        if cls.unit_menu_attribute is None:
            if condition(unit):
                return [cls.keyword]
            else:
                return []
        else:
            m = []
            for t in getattr(unit, cls.unit_menu_attribute):
                if condition(unit, t):
                    m.append(cls.keyword + " " + t)
            return m

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return cls.keyword in unit.basic_abilities

    @classmethod
    def is_almost_allowed(cls, *args):
        return cls.is_allowed(*args)

    @property
    def missing_requirements(self):
        return []


class ImmediateOrder(Order):

    never_forget_previous = True

    def immediate_action(self):
        cmd = "immediate_order_" + self.keyword
        getattr(self.unit, cmd)(*self.args)


class StopOrder(ImmediateOrder):

    keyword = "stop"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.cible

    def immediate_action(self):
        self.unit.cancel_all_orders()
        self.unit.cible = None
        self.unit.notify("order_ok")


class ImmediateCancelOrder(ImmediateOrder):

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.orders and unit.orders[-1].cancel_order == cls.keyword

    def immediate_action(self):
        self.unit.orders.pop().cancel()


class CancelTrainingOrder(ImmediateCancelOrder):

    keyword = "cancel_training"


class CancelUpgradingOrder(ImmediateCancelOrder):

    keyword = "cancel_upgrading"


class CancelBuildingOrder(ImmediateOrder):

    keyword = "cancel_building"

    def immediate_action(self):
        self.unit.player.unpay(self.unit.type.cost)
        self.unit.die()


class ModeOffensive(ImmediateOrder):

    keyword = "mode_offensive"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and unit.ai_mode == "defensive"

    def immediate_action(self):
        self.unit.ai_mode = "offensive"
        self.unit.notify("order_ok")


class ModeDefensive(ImmediateOrder):

    keyword = "mode_defensive"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and unit.ai_mode == "offensive"

    def immediate_action(self):
        self.unit.ai_mode = "defensive"
        self.unit.notify("order_ok")


class RallyingPointOrder(ImmediateOrder):

    keyword = "rallying_point"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return TrainOrder.menu(unit)

    def immediate_action(self):
        self.unit.rallying_point = self.args[0]
        self.unit.notify("order_ok")


class ComplexOrder(Order):

    def __init__(self, unit, args):
        Order.__init__(self, unit, args[1:])
        self.type = self.player.world.unit_class(args[0])

    @property
    def cost(self):
        return self.type.cost

    @property
    def food_cost(self):
        return self.type.food_cost

    @property
    def time_cost(self):
        return self.type.time_cost

    @classmethod
    def allowed_types(cls, unit):
        return getattr(unit, cls.unit_menu_attribute)

    @classmethod
    def additional_condition(cls, unit, type_name):
        return True

    @classmethod
    def is_almost_allowed(cls, unit, type_name, *unused_args):
        return type_name in cls.allowed_types(unit) \
               and type_name not in unit.player.forbidden_techs \
               and (not unit.orders or unit.orders[-1].can_be_followed) \
               and cls.additional_condition(unit, type_name)

    @classmethod
    def is_allowed(cls, unit, type_name, *args):
        return cls.is_almost_allowed(unit, type_name, *args) \
               and unit.player.has_all(unit.player.world.unit_class(type_name).requirements)

    @property
    def missing_requirements(self):
        return [r for r in self.type.requirements if not self.unit.player.has(r)]


class ProductionOrder(ComplexOrder):

    is_imperative = True
    never_forget_previous = True

    def on_queued(self):
        # first check
        result = self.unit.check_if_enough_resources(self.cost, self.food_cost)
        if result is not None:
            self.mark_as_impossible(result)
            return
        self.player.pay(self.cost)
        self.time = self.time_cost

    _previous_completeness = None

    def _notify_completeness(self):
        if self.time_cost == 0:
            return
        if self.time < 0:
            t = 0
        elif self.time > self.time_cost: # can happen when training archers
            t = self.time_cost
        else:
            t = self.time
        c = int((self.time_cost - t) * 10 / self.time_cost)
        if c != self._previous_completeness:
            self.unit.notify("completeness,%s" % c)
            self._previous_completeness = c

    _has_started = False

    def _can_start(self):
        return self.food_cost == 0 or self.player.available_food >= self.player.used_food + self.food_cost

    def _start(self):
        self._has_started = True
        self.is_deferred = False
        self.player.used_food += self.food_cost # food reservation
        self._notify_completeness()

    def _defer(self):
        self.is_deferred = True
        self.unit.notify("production_deferred")

    def complete(self): pass

    def execute(self):
        if not self._has_started:
            if self._can_start():
                self._start()
            elif not self.is_deferred:
                self._defer()
        elif self.time > 0:
            self.time -= VIRTUAL_TIME_INTERVAL
            self._notify_completeness()
        else:
            self.complete()
            self.is_complete = True

    def cancel(self, unpay=True):
        if unpay:
            self.player.unpay(self.cost)
        if self._has_started:
            self.player.used_food -= self.food_cost # end food reservation
        self.unit.notify("order_ok")


class TrainOrder(ProductionOrder):

    unit_menu_attribute = "can_train"
    keyword = "train"
    cancel_order = "cancel_training"

    def complete(self):
        x, y = self.unit.place.find_free_space(self.type.airground_type,
                                               self.unit.x, self.unit.y,
                                               player=self.player)
        if x is None:
            self.cancel()
            self.mark_as_impossible("not_enough_space")
            return
        self.player.used_food -= self.food_cost # end food reservation
        u = self.type(self.player, self.unit.place, x, y)
        u.notify("complete")
        u.take_default_order(self.unit.rallying_point)


class ResearchOrder(ProductionOrder):

    unit_menu_attribute = "can_research"
    keyword = "research"
    cancel_order = "cancel_upgrading"

    def complete(self):
        self.type.upgrade_player(self.player)
        self.unit.notify("research_complete")

    @classmethod
    def is_not_already_being_researched(cls, player, type_name):
        for u in player.units:
            for w in u.orders:
                if w.__class__ == cls and w.type.__name__ == type_name:
                    return False
        return True

    @classmethod
    def additional_condition(cls, unit, type_name):
        return type_name not in unit.player.upgrades and cls.is_not_already_being_researched(unit.player, type_name)


class UpgradeToOrder(ProductionOrder):

    unit_menu_attribute = "can_upgrade_to"
    keyword = "upgrade_to"
    cancel_order = "cancel_upgrading"
    can_be_followed = False

    @property
    def cost(self):
        return [c - self.unit.cost[i] for i, c in enumerate(self.type.cost)]

    @property
    def food_cost(self):
        return self.type.food_cost - self.unit.food_cost

    @property
    def time_cost(self):
        return self.type.time_cost - self.unit.time_cost

    def complete(self):
        player, place, x, y, hp, hp_max = self.player, self.unit.place, self.unit.x, self.unit.y, self.unit.hp, self.unit.hp_max
        leave_meadow = not self.unit.is_buildable_anywhere and self.type.is_buildable_anywhere
        consume_meadow = self.unit.is_buildable_anywhere and not self.type.is_buildable_anywhere
        if consume_meadow:
            meadow = place.find_nearest_meadow(self.unit)
            if meadow: # should check this earlier too (OK for instant upgrades though)
                x, y = meadow.x, meadow.y
                meadow.delete()
            else:
                self.unit.notify("order_impossible")
                return
        self.unit.delete()
        unit = self.type(player, place, x, y)
        if hp != hp_max:
            unit.hp = hp # TODO: adjust HP to prorata
        unit.notify("complete")
        if leave_meadow:
            Meadow(place, x, y)


    @classmethod
    def additional_condition(cls, unit, unused_type_name):
        return not unit.orders


class BasicOrder(Order):

    pass


class GoOrder(BasicOrder):

    keyword = "go"
    nb_args = 1

    _go_timer = 15 # 5 seconds

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if self.target is None:
            self.mark_as_impossible()
            return
        if hasattr(self.target, "other_side"): # go to center of arrival square if target is an exit
            self.target = self.target.other_side.place
        self.mode = "go"
        self.unit.notify("order_ok")

    def is_doing_an_imperative_attack(self):
        return self.is_imperative and self.unit.is_an_enemy(self.target)

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
        elif self.unit._near_enough_to_use(self.target) and \
            not self.is_doing_an_imperative_attack():
            self.mark_as_complete()
        elif self.unit._near_enough_to_use(self.target) and \
            self.is_doing_an_imperative_attack():
            # catapult with imperative attack on a specific target
            self.unit.cible = self.target
        elif self.unit.place == self.target:
            self.mark_as_complete()
            self.unit._go_center()
        elif self.unit.cible == self.target and \
            not self.is_doing_an_imperative_attack() and \
            self.unit.airground_type != "air":
            self._go_timer -= 1
            if self._go_timer == 0:
                self.mark_as_complete()
                self.unit.cible = None
        elif self.unit.cible is None:
            self.move_to_or_fail(self.target)


class PatrolOrder(BasicOrder):

    keyword = "patrol"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not isinstance(self.target, Square): # patrol to an object => patrol to its square instead
            try:
                self.target = self.player.get_object_by_id(self.target.place.id)
            except AttributeError:
                self.mark_as_impossible()
                return
        self.unit.notify("order_ok")
        self.target2 = self.unit.place
        self.mode = "aller"

    def execute(self):
        self.update_target()
        if self.mode == "aller":
            if self.unit.place == self.target:
                self.mode = "retour"
                self.unit._go_center()
            elif self.unit.cible is None:
                self.move_to_or_fail(self.target)
        elif self.mode == "retour":
            if self.unit.place == self.target2:
                self.mode = "aller"
                self.unit._go_center()
            elif self.unit.cible is None:
                self.move_to_or_fail(self.target2)


class GatherOrder(BasicOrder):

    keyword = "gather"
    nb_args = 1

    storage = None

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not isinstance(self.target, Deposit):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = None # decide on first execution

    def _store_cargo(self):
        self.player.store(*self.unit.cargo)
        self.unit.cargo = None

    def _extract_cargo(self):
        self.unit.cargo = (self.target.resource_type, self.target.extraction_qty)
        self.target.extract_resource()

    def execute(self):
        if self.mode is None: # decide now
            if self.unit.cargo is not None: # cargo from previous orders
                self.mode = "ramener_recolte"
            else:
                self.mode = "aller_gather"
        self.update_target()
        if self.mode == "ramener_recolte":
            if self.storage is None:
                self.storage = self.player.nearest_warehouse(self.unit.place,
                                                             self.unit.cargo[0])
                if self.storage is None:
                    self.mark_as_impossible()
                else:
                    self.unit.cible = self.unit.next_stage(self.storage)
            elif self.unit._near_enough_to_use(self.storage):
                self.mode = "stocker_recolte"
                self.unit.notify("store,%s" % self.unit.cargo[0])
                self.delai = self.unit.place.world.time + 1000 # 1 second
                self.unit.cible = None
            elif self.unit.cible is None:
                self.unit.cible = self.unit.next_stage(self.storage)
                if self.unit.cible is None:
                    self.storage = None # find a new storage
        elif self.mode == "stocker_recolte":
#            self.cible = None # cancel possible attack
            if self.unit.place.world.time > self.delai:
                self._store_cargo()
                self.mode = "aller_gather"
        elif self.mode == "aller_gather":
            if self.target is None or self.target.place is None: # resource exhausted
                self.player.on_resource_exhausted()
                self.mark_as_impossible()
                self.unit._go_center()
            elif self.unit._near_enough_to_use(self.target):
                self.mode = "gather"
                self.delai = self.unit.place.world.time + self.target.extraction_time
                self.unit.cible = None
            elif self.unit.cible is None:
                self.move_to_or_fail(self.target)
##                if self.unit.cible is None: # exhausted or impossible to reach
##                    self.player.on_resource_exhausted()
        elif self.mode == "gather": # XXX TODO: check if a fight or a teleportation is going on
#            self.cible = None # cancel possible attack
            if self.target is None or self.target.place is None: # resource exhausted
                self.player.on_resource_exhausted()
                self.mark_as_impossible()
            elif self.unit.place.world.time > self.delai:
                self._extract_cargo()
                self.mode = "ramener_recolte"
                self.storage = None


class ComputerOnlyOrder(Order):

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return not unit.player.is_human()


class AutoAttackOrder(ComputerOnlyOrder):

    keyword = "auto_attack"

    def on_queued(self):
        pass

    def execute(self):
        if not self.unit.cible:
            if self.unit.place.contains_enemy(self.player):
                self.unit.choose_enemy()
            else:
                self.unit.cible = self.unit.next_stage_enemy()


class AutoExploreOrder(ComputerOnlyOrder):

    keyword = "auto_explore"
    is_imperative = True

    def on_queued(self):
        pass

    def execute(self):
        if len(self.player.world.squares) != len(self.player.observed_before_squares):
            self.unit.is_an_explorer = True
            if self.unit.auto_explore():
                self.mark_as_complete()
        else:
            self.mark_as_complete()


class RepairOrder(BasicOrder):

    keyword = "repair"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not getattr(self.target, "is_repairable", False):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = "aller_construire"

    def execute(self):
        self.update_target()
        if self.target is None or self.target.place is None or self.target.is_fully_repaired:
            # if the building has been destroyed or cancelled or completely repaired then the work is complete
            self.mark_as_complete()
            self.unit.cible = None
        elif self.mode == "aller_construire":
            if self.unit._near_enough_to_use(self.target):
                self.mode = "construire"
                self.unit.cible = None
            elif self.unit.cible is None:
                self.move_to_or_fail(self.target)
        elif self.mode == "construire":
            self.target.be_built()


class BuildPhaseTwoOrder(RepairOrder):

    keyword = "build_phase_two"


class BuildOrder(ComplexOrder):

    unit_menu_attribute = "can_build"
    keyword = "build"
    nb_args = 1

    def __eq__(self, other):
        # BuildOrder.id is used to make the difference between 2 successive
        # "no meadow needed" building projects on the same square. Orders
        # given for the same group and at the same "time" (same cmd_order call)
        # have the same id.
        return self.__class__ == other.__class__ and self.type == other.type \
               and getattr(self.target, "id", None) == getattr(other.target, "id", None) \
               and self.id == other.id

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not self.type.is_buildable_anywhere \
           and not getattr(self.target, "is_a_building_land", False):
            self.mark_as_impossible("cannot_build_here")
            return
        if not self.player.resources_are_reserved(self):
            result = self.unit.check_if_enough_resources(self.cost, self.food_cost)
            if result is not None:
                self.mark_as_impossible(result)
                return
        if self.unit.next_stage(self.target) is None and self.target is not self.unit.place: # target must be reachable
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        # reserve resources
        self.player.reserve_resources_if_needed(self)

    def execute(self):
        self.update_target()
        # second check
        if self.target is None or self.target.place is None: # for example, meadow already used
            self.mark_as_impossible()
            return
        # execute
        if self.target is self.unit.place or \
           self.target.place is self.unit.place:
            self.player.free_resources(self)
            x, y = self.unit.place.find_free_space(self.type.airground_type,
                                                   self.target.x, self.target.y,
                                                   player=self.player)
            if x is None:
                self.cancel()
                self.mark_as_impossible("not_enough_space")
                return
            self.unit._put_building_site(self.type, self.target)
        elif self.unit.cible is None:
            self.move_to_or_fail(self.target)


class UseOrder(ComplexOrder):

    is_imperative = True
    unit_menu_attribute = "can_use"
    keyword = "use"

    @property
    def nb_args(self):
        if self.type.effect_target == ["ask"]:
            return 1
        return 0

    def _group_has_enough_mana(self, mana):
        if self.unit.player.group_had_enough_mana:
            return True
        # assertion: the order is recent (so player.group is relevant)
        # assertion: every unit in the group is concerned by the order
        for u in self.unit.player.group:
            if u.mana > mana:
                self.unit.player.group_had_enough_mana = True
                return True
        return False

    @property
    def _target_type(self):
        return getattr(self, "%s_target_type" % self.type.effect[0], "square")

    def on_queued(self):
        if self.type.effect_target == ["ask"]:
            if self.args:
                self.target = self.player.get_object_by_id(self.args[0])
            else:
                self.target = None
            if self.target is None:
                self.mark_as_impossible()
                return
            if self._target_type == "square":
                # make sure that the target is a square
                if not isinstance(self.target, Square):
                    if  hasattr(self.target, "place") and isinstance(self.target.place, Square):
                        self.target = self.target.place
                    else:
                        self.mark_as_impossible()
                        return
        elif self.type.effect_target == ["random"]:
            self.target = worldrandom.choice(self.player.world.squares)
        else:
            self.target = self.unit.place
        # check cost
        if self.unit.mana < self.type.mana_cost:
            if self._group_has_enough_mana(self.type.mana_cost):
                self.mark_as_complete() # ignore silently
            else:
                self.mark_as_impossible("not_enough_mana")
            return
        self.unit.notify("order_ok")

    def _target_square(self):
        if self._target_type == "square":
            return self.target
        return self.target.place

    def execute(self):
        # check if the target has disappeared
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
            return
        # ignore silently if it is not necessary
        if getattr(self, "%s_is_not_necessary" % self.type.effect[0])():
            self.mark_as_complete() # ignore silently (to save mana when giving the same order to many casters)
            return
        # move closer eventually
        if self.type.effect_range == ["square"]:
            if self._target_square() != self.unit.place:
                self.move_to_or_fail(self.target)
                return
        elif self.type.effect_range == ["nearby"]:
            if self._target_square() not in self.unit.place.neighbours \
                         and self._target_square() is not self.unit.place:
                self.move_to_or_fail(self.target)
                return
        # the target is close enough, but is the target real?
        if self.type.effect[0] == "conversion" and self.target.is_memory:
            self.mark_as_impossible()
            return
        # check cost
        if self.unit.mana < self.type.mana_cost:
            self.mark_as_impossible("not_enough_mana")
            return
        # execute order
        getattr(self, "execute_%s" % self.type.effect[0])()
        self.unit.mana -= self.type.mana_cost
        self.unit.notify("use_complete,%s" % self.type.type_name,
                         universal=self.type.universal_notification)
        self.mark_as_complete()

    # NOTE: replaced can_receive(t, self.player) with can_receive(t)
    # because teleportation would always win.

    def teleportation_is_not_necessary(self):
        units = [u for u in self.player.units
                 if u.place == self.unit.place and isinstance(u, Unit)]
        types = set([u.airground_type for u in units])
        if self.target is self.unit.place:
            return True
        elif not [t for t in types if self.target.can_receive(t)]:
            self.mark_as_impossible("not_enough_space") # XXX probably not the right place to signal a problem
            return True

    def execute_teleportation(self):
        units = [u for u in self.player.units
                 if u.place == self.unit.place and isinstance(u, Unit)]
        # teleport weak units after the strong ones so peasants in defensive mode don't systematically flee
        for u in sorted(units, key=lambda x: x.menace, reverse=True):
            if self.target.can_receive(u.airground_type):
                u.move_to(self.target, None, None)

    def recall_is_not_necessary(self):
        units = [u for u in self.player.units
                 if u.place == self.target and isinstance(u, Unit)]
        if not units:
            return True
        types = set([u.airground_type for u in units])
        if self.target is self.unit.place:
            return True
        elif not [t for t in types if self.unit.place.can_receive(t)]:
            self.mark_as_impossible("not_enough_space") # XXX probably not the right place to signal a problem
            return True

    def execute_recall(self):
        units = [u for u in self.player.units
                 if u.place == self.target and isinstance(u, Unit)]
        # teleport weak units after the strong ones so peasants in defensive mode don't systematically flee
        for u in sorted(units, key=lambda x: x.menace, reverse=True):
            if self.unit.place.can_receive(u.airground_type):
                u.move_to(self.unit.place, None, None)

    conversion_target_type = "unit"

    def conversion_is_not_necessary(self):
        return not self.unit.is_an_enemy(self.target)

    def execute_conversion(self):
        self.target.set_player(self.unit.player)

    def summon_is_not_necessary(self):
        return False

    def execute_summon(self):
        self.unit.player.lang_add_units(
            [self.target.name] + self.type.effect[2:],
            decay=to_int(self.type.effect[1]),
            notify=False)

    def raise_dead_is_not_necessary(self):
        return not [o for o in self.target.objects if isinstance(o, Corpse)]

    def execute_raise_dead(self):
        self.unit.player.lang_add_units(
            [self.target.name] + self.type.effect[2:],
            decay=to_int(self.type.effect[1]),
            from_corpse=True,
            notify=False)

    def resurrection_is_not_necessary(self):
        return not [o for o in self.target.objects if isinstance(o, Corpse) and o.unit.player is self.unit.player]

    def execute_resurrection(self):
        corpses = [o for o in self.target.objects if isinstance(o, Corpse) and o.unit.player is self.unit.player]
        for _ in range(int(self.type.effect[1])):
            if corpses:
                c = corpses.pop()
                u = c.unit
                u.player = None
                u.place = None
                u.id = None # so the unit will be added to world.active_objects
                u.hp = u.hp_max / 3
                u.set_player(self.unit.player)
                u.move_to(c.place, c.x, c.y)
                if u.decay:
                    u.time_limit = u.world.time + u.decay
                c.delete()
            else:
                break

    @classmethod
    def additional_condition(cls, unused_unit, type_name):
        e = get_rule(type_name, "effect")
        return e and hasattr(cls, "execute_%s" % e[0])


class TransportOrder(Order):

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.transport_capacity > 0


class LoadOrder(TransportOrder):

    keyword = "load"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if self.target is None or \
           self.unit.player is not getattr(self.target, "player", None):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None or not self.unit.have_enough_space(self.target):
            self.mark_as_impossible()
        elif self.unit.place != self.target.place:
            self.move_to_or_fail(self.target.place)
        else:
            self.mark_as_complete()
            self.unit.load(self.target)


class EnterOrder(ImmediateOrder):

    keyword = "enter"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return True # XXX something more precise? (unit is transportable, target is a transport with enough space?)

    def immediate_action(self):
        self.target = self.player.get_object_by_id(self.args[0])
        self.target.take_order(["load", self.unit.id], forget_previous=False)
        self.unit.take_order(["go", self.target.id])


class LoadAllOrder(TransportOrder):

    keyword = "load_all"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not isinstance(self.target, Square) and hasattr(self.target, "place"):
            self.target = self.target.place
        if self.target is None:
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
        elif self.unit.place != self.target:
            self.move_to_or_fail(self.target)
        else:
            self.mark_as_complete()
            self.unit.load_all()


class UnloadAllOrder(TransportOrder):

    keyword = "unload_all"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        # first check
        if not isinstance(self.target, Square) and hasattr(self.target, "place"):
            self.target = self.target.place
        if self.target is None:
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
        elif self.unit.place != self.target:
            self.move_to_or_fail(self.target)
        else:
            self.mark_as_complete()
            self.unit.unload_all()


class Ability(object): # or UnitOption or UnitMenuItem or ActiveAbility or SpecialAbility

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES # XXX not implemented (really useful anyway?)
    time_cost = 0
    requirements = ()
    food_cost = 0
    mana_cost = 0
    effect = None
    effect_target = ["self"]
    effect_range = ["square"]
    universal_notification = False

    cls = object # XXX


class Upgrade(object): # or Tech

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    time_cost = 0
    requirements = ()
    food_cost = 0
    effect = None

    cls = object # XXX

    def __init__(self, name, dct):
        self.type_name = name
        self.__name__ = name
        for k, v in dct.items():
            if k == "class":
                continue
            if hasattr(self, k) and not callable(getattr(self, k)):
                setattr(self, k, v)
            else:
                warning("in %s: %s doesn't have any attribute called '%s'", name, self.__class__.__name__, k)

    def upgrade_player(self, player):
        for unit in player.units:
            if self.type_name in unit.can_use:
                getattr(self, "effect_%s" % self.effect[0])(unit, player.level(self.type_name), *self.effect[1:])
        player.upgrades.append(self.type_name)

    def upgrade_unit_to_player_level(self, unit):
        for level in range(unit.player.level(self.type_name)):
            getattr(self, "effect_%s" % self.effect[0])(unit, level, *self.effect[1:])

    def effect_bonus(self, unit, start_level, stat, base, incr=0):
        setattr(unit, stat, getattr(unit, stat) + int(base) + int(incr) * start_level)
#        warning("next level for '%s' now %s", stat, getattr(unit, stat))

    def effect_apply_bonus(self, unit, start_level, stat):
        self.effect_bonus(unit, start_level, stat, getattr(unit, stat + "_bonus", 0))


# build a dictionary containing order classes, by keyword
# for example: ORDERS_DICT["go"] == GoOrder
ORDERS_DICT = dict([(_v.keyword, _v) for _v in locals().values()
                    if hasattr(_v, "keyword") and issubclass(_v, Order)])
