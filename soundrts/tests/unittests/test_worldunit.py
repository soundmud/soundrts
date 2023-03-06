from unittest.mock import Mock, call

from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION
from soundrts.worldroom import Square, Inside
from soundrts.worldunit import Unit, Soldier


class _Unit(Unit):
    action = None
    x = 1
    y = 2

    def __init__(self):
        self.orders = []
        self.take_order = Mock()
        self.inside = Inside(self)


class _Square(Square):
    place = "world"

    def __init__(self):
        self.id = id(self)


def test_next_stage():
    unit = _Unit()
    assert unit.next_stage(None) is None

    unit.place = _Square()
    assert unit.next_stage(unit.place) is None

    target = _Unit()
    target.place = unit.place
    assert unit.next_stage(target) is target

    target.place = None
    assert unit.next_stage(target) is None

    target.place = _Square()
    unit.place = target.inside
    assert unit.next_stage(target) is None


def _counterattack_setup(can_go=True):
    # u = Unit(None, None, 0, 0)
    unit = _Unit()
    unit.speed = 1
    unit.damage = 1
    unit.ai_mode = "offensive"
    unit.place = _Square()
    unit._can_go = Mock(return_value=can_go)
    place = _Square()
    return place, unit


def test_counterattack():
    place, unit = _counterattack_setup()

    unit.counterattack(place)

    counterattack, go_back = unit.take_order.call_args_list
    assert counterattack == call(["go", place.id])
    assert go_back == call(["go", f"zoom-{unit.place.id}-{unit.x}-{unit.y}"], forget_previous=False)


def test_counterattack_if_cannot_go():
    place, unit = _counterattack_setup(can_go=False)

    unit.counterattack(place)

    unit.take_order.assert_not_called()


def test_counterattack_if_defensive_mode():
    place, unit = _counterattack_setup()
    unit.ai_mode = "defensive"

    unit.counterattack(place)

    unit.take_order.assert_not_called()


_damage_vs_rules = """
def pikeman
class soldier
damage 6
damage_vs cavalry 12

def cavalry
class soldier

def light_cavalry
is_a cavalry

def light_cavalry_subtype
is_a light_cavalry

def horse_archer
is_a cavalry archer
"""


def test_damage_vs():
    rules.load(_damage_vs_rules, base_classes={"soldier": Soldier})

    # basic case
    a_pikeman = rules.classes["pikeman"].create_from_nowhere()
    a_cavalry = rules.classes["cavalry"].create_from_nowhere()
    assert a_pikeman._base_damage_versus(a_pikeman) == 6 * PRECISION
    assert a_pikeman._base_damage_versus(a_cavalry) == 12 * PRECISION

    # "inheritance"
    a_light_cavalry = rules.classes["light_cavalry"].create_from_nowhere()
    assert a_pikeman._base_damage_versus(a_light_cavalry) == 12 * PRECISION

    # second level of "inheritance"
    a_light_cavalry_subtype = rules.classes["light_cavalry_subtype"].create_from_nowhere()
    assert a_pikeman._base_damage_versus(a_light_cavalry_subtype) == 12 * PRECISION

    # multiple "inheritance"
    a_horse_archer = rules.classes["horse_archer"].create_from_nowhere()
    assert a_pikeman._base_damage_versus(a_horse_archer) == 12 * PRECISION


_armor_vs_rules = """
def archer
class soldier

def horse_archer
is_a cavalry archer

def heavy
class soldier
armor 1
armor_vs archer 2
"""


def test_armor_vs():
    rules.load(_armor_vs_rules, base_classes={"soldier": Soldier})

    # basic case
    an_archer = rules.classes["archer"].create_from_nowhere()
    a_heavy = rules.classes["heavy"].create_from_nowhere()
    assert a_heavy.armor_versus(a_heavy) == 1 * PRECISION
    assert a_heavy.armor_versus(an_archer) == 2 * PRECISION

    # multiple "inheritance"
    a_horse_archer = rules.classes["horse_archer"].create_from_nowhere()
    assert a_heavy.armor_versus(a_horse_archer) == 2 * PRECISION
