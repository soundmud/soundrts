from definitions import MAX_NB_OF_RESOURCE_TYPES
from lib.log import warning


class Upgrade(object): # or Tech

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    count_limit = 0
    time_cost = 0
    requirements = ()
    food_cost = 0
    effect = None

    cls = object # useful?

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
        if stat == "damage": unit.damage_level += 1
#        warning("next level for '%s' now %s", stat, getattr(unit, stat))

    def effect_apply_bonus(self, unit, start_level, stat):
        self.effect_bonus(unit, start_level, stat, getattr(unit, stat + "_bonus", 0))
        if stat == "damage": unit.damage_level += 1
