from constants import MAX_NB_OF_RESOURCE_TYPES


class Ability(object): # or UnitOption or UnitMenuItem or ActiveAbility or SpecialAbility

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES # XXX not implemented (really useful anyway?)
    count_limit = 0 # ugly but necessary; used by ComplexOrder.is_allowed()
    time_cost = 0
    requirements = ()
    food_cost = 0
    mana_cost = 0
    effect = None
    effect_target = ["self"]
    effect_range = ["square"]
    universal_notification = False

    cls = object # XXX
