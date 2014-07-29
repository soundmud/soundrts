from constants import MAX_NB_OF_RESOURCE_TYPES, ORDERS_QUEUE_LIMIT, VIRTUAL_TIME_INTERVAL
from definitions import rules
from nofloat import to_int
import worldrandom
from worldresource import Meadow, Deposit, Corpse
from worldroom import Square


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
                 if u.place == self.unit.place and u.is_teleportable]
        types = set([u.airground_type for u in units])
        if self.target is self.unit.place:
            return True
        elif not [t for t in types if self.target.can_receive(t)]:
            self.mark_as_impossible("not_enough_space") # XXX probably not the right place to signal a problem
            return True

    def execute_teleportation(self):
        units = [u for u in self.player.units
                 if u.place == self.unit.place and u.is_teleportable]
        # teleport weak units after the strong ones so peasants in defensive mode don't systematically flee
        for u in sorted(units, key=lambda x: x.menace, reverse=True):
            if self.target.can_receive(u.airground_type):
                u.move_to(self.target, None, None)

    def recall_is_not_necessary(self):
        units = [u for u in self.player.units
                 if u.place == self.target and u.is_teleportable]
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
                 if u.place == self.target and u.is_teleportable]
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


# build a dictionary containing order classes, by keyword
# for example: ORDERS_DICT["go"] == GoOrder
ORDERS_DICT = dict([(_v.keyword, _v) for _v in locals().values()
                    if hasattr(_v, "keyword") and issubclass(_v, Order)])

