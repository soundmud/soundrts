from .definitions import MAX_NB_OF_RESOURCE_TYPES


def is_an_upgrade(o):
    return hasattr(o, "upgrade_player")


class Upgrade:  # or Tech

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES  # TODO: remove this
    count_limit = 0
    time_cost = 0
    requirements = ()
    food_cost = 0
    effect = None

    cls = object  # useful?

    @classmethod
    def upgrade_player(cls, player):
        for unit in player.units:
            if cls.type_name in unit.can_use:
                getattr(cls, "effect_%s" % cls.effect[0])(
                    unit, player.level(cls.type_name), *cls.effect[1:]
                )
        player.upgrades.append(cls.type_name)

    @classmethod
    def upgrade_unit_to_player_level(cls, unit):
        for level in range(unit.player.level(cls.type_name)):
            getattr(cls, "effect_%s" % cls.effect[0])(unit, level, *cls.effect[1:])

    @classmethod
    def effect_bonus(cls, unit, start_level, stat, base, incr=0):
        setattr(unit, stat, getattr(unit, stat) + int(base) + int(incr) * start_level)
        if stat == "damage":
            unit.damage_level += 1

    @classmethod
    def effect_apply_bonus(cls, unit, start_level, stat):
        cls.effect_bonus(unit, start_level, stat, getattr(unit, stat + "_bonus", 0))
        if stat == "damage":
            unit.damage_level += 1
