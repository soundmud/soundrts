from constants import MAX_NB_OF_RESOURCE_TYPES, ORDERS_QUEUE_LIMIT, VIRTUAL_TIME_INTERVAL
from definitions import rules
from lib.log import info
from lib.nofloat import to_int, PRECISION
import worldrandom
from worldaction import AttackAction, MoveXYAction
from worldresource import Meadow, Deposit, Corpse
from worldroom import Square
from soundrts.lib.nofloat import square_of_distance


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
            self.unit.stop()
            self.__first_update = False
        self.execute()

    @property
    def player(self):
        return self.unit.player

    @property
    def world(self):
        return self.unit.world

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
           type(t).__name__ != "ZoomTarget" and \
           t not in p.world.squares and \
           t not in p.perception and \
           t not in p.memory:
            self.target = p.get_object_by_id(t.id)

    def _group_is_ready(self):
        for u in self.player.units:
            if u is not self.unit and u.orders and u.orders[0] == self \
               and u.place is not self.unit.place:
                return False
        return True

    def _grouped_attack(self, target):
        # goal: make sure no unit starts deploying instead of attacking
        # (the recently arrived units used to deploy before attacking)
        self.unit.notify("attack")
        for u in self.player.units:
            if u.orders and u.orders[0] == self and u.place is self.unit.place:
                u.start_moving_to(target)

    def _default_move_to_or_fail(self, target):
        self.unit.start_moving_to(target)
        if self.unit.is_idle: # target is unreachable
            self.mark_as_impossible()
            self.unit.deploy() # do not block the path

    def _smart_move_to_or_fail(self, target):
        self.unit.start_moving_to(target, avoid=self.player.smart_units)
        if self.unit.is_idle and isinstance(self, (GoOrder, PatrolOrder)):    
            # eventually attack the obstacle
            next_square = self.unit.next_stage(target)
            try:
                next_square = next_square.other_side.place
            except AttributeError:
                pass
            if self.player.enemy_menace(next_square) == 0: # no obstacle yet
                self.unit.start_moving_to(next_square)
            elif next_square is target:
                if self.player.balance(next_square, self.unit.place) > 1.1 \
                   or self._group_is_ready():
                    self._grouped_attack(next_square)
                    return
                else:
                    self.unit.deploy()
                    return
            elif self.player.balance(next_square, self.unit.place) > 1.1:
                info("attack through")
                self._grouped_attack(next_square)
            else:
                info("wait")
                self.unit.deploy()
                return
        if self.unit.is_idle: # target is unreachable
            self.mark_as_impossible()
            self.unit.deploy() # do not block the path

    def move_to_or_fail(self, target):
        if self.unit.speed == 0:
            self.mark_as_impossible()
            return
        if self.player.smart_units:
            self._default_move_to_or_fail(target)
        else:
            self._smart_move_to_or_fail(target)

    def immediate_action(self):
        if len(self.unit.orders) >= ORDERS_QUEUE_LIMIT:
            self.unit.notify("order_impossible,the_queue_is_full")
        # check food requirement only if the queue is empty
        elif not self.unit.orders and self.food_cost != 0 \
             and self.unit.player.available_food < self.unit.player.used_food + self.food_cost:
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
        return not unit.is_idle or unit.orders

    def immediate_action(self):
        self.unit.cancel_all_orders()
        self.unit.stop()
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


class RallyingPointOrder(ImmediateOrder):

    keyword = "rallying_point"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return TrainOrder.menu(unit)

    def immediate_action(self):
        self.unit.rallying_point = self.args[0]
        self.unit.notify("order_ok")


class JoinGroupOrder(ImmediateOrder):

    keyword = "join_group"
    nb_args = 1

    def immediate_action(self):
        group_name = self.args[0]
        if group_name not in self.player.groups:
            self.player.groups[group_name] = []
        if self.unit.group != self.player.groups[group_name]:
            self.unit.group = self.player.groups[group_name]
            self.unit.group.append(self.unit)
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
               and cls.additional_condition(unit, type_name) \
               and unit.player.check_count_limit(type_name)

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
        blocked_exit = self.unit.blocked_exit
        if consume_meadow:
            meadow = place.find_nearest_meadow(self.unit)
            if meadow:
                x, y = meadow.x, meadow.y
                meadow.delete()
            else:
                self.unit.notify("order_impossible")
                return
        self.unit.delete()
        unit = self.type(player, place, x, y)
        if blocked_exit:
            unit.block(blocked_exit)
        if hp != hp_max:
            unit.hp = hp
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

    def __eq__(self, other):
        # smart units with the same "go" order will behave as a group
        # (cf move_to_or_fail)
        return self.__class__ == other.__class__ and \
            getattr(self.target, "id", None) == getattr(other.target, "id", None) and \
            self._creation_time == other._creation_time

    def on_queued(self):
        self._creation_time = self.world.time
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        if hasattr(self.target, "other_side"): # target is an exit
            # the new target is the square on the other side
            self.target = self.target.other_side.place
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
        elif self.unit.is_in_position(self.target): # square or subsquare
            self.unit.hold(self.target)
            self.mark_as_complete()
        elif self.unit._near_enough(self.target):
            self.mark_as_complete()
        elif self.unit.is_idle:
            self.move_to_or_fail(self.target)


class AttackOrder(BasicOrder):

    keyword = "attack"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:
            self.mark_as_impossible()
            return
        if self.unit._near_enough_to_aim(self.target):
            self.unit.action = AttackAction(self.unit, self.target)
        elif self.unit.is_idle:
            self.move_to_or_fail(self.target)


class PatrolOrder(BasicOrder):

    keyword = "patrol"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not isinstance(self.target, Square): # patrol to an object
            # patrol to its square instead
            try:
                self.target = self.player.get_object_by_id(self.target.place.id)
            except AttributeError:
                self.mark_as_impossible()
                return
        self.unit.notify("order_ok")
        self.target2 = self.unit.place
        self.mode = "go"

    def execute(self):
        self.update_target()
        if self.mode == "go":
            if self.unit.place == self.target:
                self.mode = "go_back"
                self.unit.deploy()
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "go_back":
            if self.unit.place == self.target2:
                self.mode = "go"
                self.unit.deploy()
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target2)


class GatherOrder(BasicOrder):

    keyword = "gather"
    nb_args = 1

    storage = None

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not isinstance(self.target, Deposit):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = None

    def _store_cargo(self):
        self.player.store(*self.unit.cargo)
        self.unit.cargo = None

    def _extract_cargo(self):
        self.unit.cargo = (self.target.resource_type, self.target.extraction_qty)
        self.target.extract_resource()

    def execute(self):
        if self.mode is None:
            if self.unit.cargo is not None: # cargo from previous orders
                self.mode = "bring_back"
            else:
                self.mode = "go_gather"
        self.update_target()
        if self.mode == "bring_back":
            if self.storage is None:
                self.storage = self.player.nearest_warehouse(self.unit.place,
                                                             self.unit.cargo[0])
                if self.storage is None:
                    self.mark_as_impossible()
                else:
                    self.unit.start_moving_to(self.storage)
            elif self.unit._near_enough(self.storage):
                self.mode = "store"
                self.unit.notify("store,%s" % self.unit.cargo[0])
                self.delay = self.unit.place.world.time + 1000 # 1 second
                self.unit.stop()
            elif self.unit.is_idle:
                self.unit.start_moving_to(self.storage)
                if self.unit.is_idle:
                    self.storage = None # find a new storage
        elif self.mode == "store":
            if self.unit.place.world.time > self.delay:
                self._store_cargo()
                self.mode = "go_gather"
        elif self.mode == "go_gather":
            if self.target is None or self.target.place is None: # resource exhausted
                self.mark_as_impossible()
                self.unit.deploy()
            elif self.unit._near_enough(self.target):
                self.mode = "gather"
                self.delay = self.unit.place.world.time + self.target.extraction_time
                self.unit.stop()
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "gather":
            if self.target is None or self.target.place is None: # resource exhausted
                self.mark_as_impossible()
            elif self.unit.place.world.time > self.delay:
                self._extract_cargo()
                self.mode = "bring_back"
                self.storage = None


class ComputerOnlyOrder(Order):

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return not unit.player.is_human()


class AutoAttackOrder(ComputerOnlyOrder):

    keyword = "auto_attack"
    is_imperative = True

    def on_queued(self):
        pass

    def execute(self):
        if self.unit.is_idle:
            self.unit.start_moving_to_enemy()


class AutoExploreOrder(ComputerOnlyOrder):

    keyword = "auto_explore"
    is_imperative = True

    def on_queued(self):
        player = self.unit.player
        world = player.world
        if getattr(player, "_places_to_explore", None) is None:
            player._places_to_explore = [world.grid[name]
                                         for name in world.starting_squares]
            worldrandom.shuffle(player._places_to_explore)
            player._already_explored = set()

    def execute(self):
        self.unit.auto_explore()


class WaitOrder(ComputerOnlyOrder):

    keyword = "wait"
    nb_args = 1
    is_imperative = True

    def on_queued(self):
        self._must_deploy = True
        self.target = self.player.get_object_by_id(self.args[0])

    def execute(self):
        if self._must_deploy:
            self.unit.deploy()
            self._must_deploy = False
        if self.player.time_has_come(self.target):
            self.mark_as_complete()


class BlockOrder(BasicOrder):

    keyword = "block"
    nb_args = 1
    is_imperative = True

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not getattr(self.target, "is_an_exit", False):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = "go_block"

    def execute(self):
        self.update_target()
        if self.mode == "go_block":
            if self.unit._near_enough(self.target):
                self.mode = "block"
                self.unit.stop()
                self.unit.move_on_border(self.target)
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "block":
            self.unit.block(self.target)


class RepairOrder(BasicOrder):

    keyword = "repair"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not getattr(self.target, "is_repairable", False):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")
        self.mode = "go_build"

    def execute(self):
        self.update_target()
        if self.target is None or self.target.place is None \
           or self.target.is_fully_repaired: # destroyed, cancelled or fully repaired
            self.mark_as_complete()
            self.unit.stop()
        elif self.mode == "go_build":
            if self.unit._near_enough(self.target):
                self.mode = "build"
                self.unit.stop()
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "build":
            self.target.be_built(self.unit)


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
        if self.type.is_buildable_on_exits_only:
            if not getattr(self.target, "is_an_exit", False):
                self.mark_as_impossible("cannot_build_here")
                return
        elif not self.type.is_buildable_anywhere:
            if not getattr(self.target, "is_a_building_land", False):
                self.target = getattr(self.target, "building_land", None)
                if self.target is None:
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
        self.player.reserve_resources_if_needed(self)

    def execute(self):
        self.update_target()
        if self.target is None or self.target.place is None: # meadow already used
            self.mark_as_impossible()
            return
        if self.target is self.unit.place or self.target.place is self.unit.place:
            self.player.free_resources(self)
            x, _ = self.unit.place.find_free_space(self.type.airground_type,
                                                   self.target.x, self.target.y,
                                                   player=self.player)
            if x is None:
                self.cancel()
                self.mark_as_impossible("not_enough_space")
                return
            if self.player.check_count_limit(self.type.type_name):
                self.unit._put_building_site(self.type, self.target)
            else:
                self.cancel()
                self.mark_as_impossible("count_limit_reached")
        elif self.unit.is_idle:
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
                if not hasattr(self.target, "x"):
                    self.mark_as_impossible()
                    return
        elif self.type.effect_target == ["random"]:
            self.target = worldrandom.choice(self.player.world.squares)
        elif self.type.effect_target == ["self"]:
            self.target = self.unit
        if self.unit.mana < self.type.mana_cost:
            if self._group_has_enough_mana(self.type.mana_cost):
                self.mark_as_complete() # ignore silently
            else:
                self.mark_as_impossible("not_enough_mana")
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None: # target has disappeared
            self.mark_as_impossible()
            return
        if getattr(self, "%s_is_not_necessary" % self.type.effect[0])():
            # ignore silently (to save mana when giving the same order to many casters)
            self.mark_as_complete()
            return
        if square_of_distance(self.target.x, self.target.y, self.unit.x, self.unit.y) \
           > self.type.effect_range * self.type.effect_range:
            self.move_to_or_fail(self.target) # move closer
            return
        if self.type.effect[0] == "conversion" and self.target.is_memory:
            self.mark_as_impossible()
            return
        if self.unit.mana < self.type.mana_cost:
            self.mark_as_impossible("not_enough_mana")
            return
        getattr(self, "execute_%s" % self.type.effect[0])()
        self.unit.mana -= self.type.mana_cost
        self.unit.notify("use_complete,%s" % self.type.type_name,
                         universal=self.type.universal_notification)
        self.mark_as_complete()

    def teleportation_targets(self):
        return self.unit.world.get_objects(self.unit.x, self.unit.y,
                                           self.type.effect_radius,
                    filter=lambda x: x.player is self.player and x.is_teleportable)

    def teleportation_is_not_necessary(self):
        units = self.teleportation_targets()
        types = set([u.airground_type for u in units])
        if self.target is self.unit.place:
            return True
        # NOTE: replaced can_receive(t, self.player) with can_receive(t)
        # because teleportation would always win.
        elif not [t for t in types if self.target.can_receive(t)]:
            self.mark_as_impossible("not_enough_space")
            return True

    def execute_teleportation(self):
        for u in self.teleportation_targets():
            if self.target.can_receive(u.airground_type):
                u.move_to(self.target, None, None)

    def recall_targets(self):
        return self.unit.world.get_objects(self.target.x, self.target.y,
                                           self.type.effect_radius,
                    filter=lambda x: x.player is self.player and x.is_teleportable)

    def recall_is_not_necessary(self):
        units = self.recall_targets()
        if not units:
            return True
        types = set([u.airground_type for u in units])
        if self.target is self.unit.place:
            return True
        elif not [t for t in types if self.unit.place.can_receive(t)]:
            self.mark_as_impossible("not_enough_space")
            return True

    def execute_recall(self):
        for u in self.recall_targets():
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
            self.type.effect[2:],
            target=self.target,
            decay=to_int(self.type.effect[1]),
            notify=False)

    def raise_dead_targets(self):
        return self.unit.world.get_objects(self.target.x, self.target.y,
                                           self.type.effect_radius,
                                           filter=lambda x: isinstance(x, Corpse))

    def raise_dead_is_not_necessary(self):
        return not self.raise_dead_targets()

    def execute_raise_dead(self):
        corpses = sorted(
            self.raise_dead_targets(),
            key=lambda o: square_of_distance(self.target.x, self.target.y, o.x, o.y))
        self.unit.player.lang_add_units(
            self.type.effect[2:],
            decay=to_int(self.type.effect[1]),
            from_corpse=True,
            corpses=corpses,
            notify=False)

    def resurrection_targets(self):
        return self.unit.world.get_objects(
            self.target.x, self.target.y, self.type.effect_radius,
            filter=lambda x: isinstance(x, Corpse) and x.unit.player is self.unit.player)

    def resurrection_is_not_necessary(self):
        return not self.resurrection_targets()

    def execute_resurrection(self):
        corpses = sorted(
            self.resurrection_targets(),
            key=lambda o: square_of_distance(self.target.x, self.target.y, o.x, o.y))
        for _ in range(int(self.type.effect[1])):
            if corpses:
                c = corpses.pop(0)
                u = c.unit
                if not self.player.check_count_limit(u.type_name):
                    continue
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
        e = rules.get(type_name, "effect")
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
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return True

    def immediate_action(self):
        self.target = self.player.get_object_by_id(self.args[0])
        self.target.take_order(["load", self.unit.id], forget_previous=False)
        self.unit.take_order(["go", self.target.id])


class LoadAllOrder(TransportOrder):

    keyword = "load_all"
    nb_args = 1

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
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


# build a dictionary containing order classes
# for example: ORDERS_DICT["go"] == GoOrder
ORDERS_DICT = dict([(_v.keyword, _v) for _v in locals().values()
                    if hasattr(_v, "keyword") and issubclass(_v, Order)])
