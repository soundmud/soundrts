from definitions import MAX_NB_OF_RESOURCE_TYPES
from soundrts.lib.nofloat import PRECISION


class Ability(object): # or UnitOption or UnitMenuItem or ActiveAbility or SpecialAbility

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES # required by the user interface
    count_limit = 0 # ugly but necessary; used by ComplexOrder.is_allowed()
    time_cost = 0 # doesn't seem to be required
    requirements = ()
    food_cost = 0
    mana_cost = 0
    effect = None
    effect_target = ["self"]
    effect_range = 6 * PRECISION # "square"
    effect_radius = 6 * PRECISION
    universal_notification = False

    cls = object # probably not used
