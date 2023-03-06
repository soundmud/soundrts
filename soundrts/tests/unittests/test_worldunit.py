from unittest.mock import Mock, call

from soundrts.worldroom import Square, Inside
from soundrts.worldunit import Unit


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
