from soundrts.worldroom import Square
from soundrts.worldunit import Unit


class Unit(Unit):  # type: ignore
    def __init__(self):
        pass


class Square(Square):  # type: ignore
    def __init__(self):
        pass

    place = "world"


def test_next_stage():
    u = Unit()
    #    assert u.next_stage(None) is None
    u.place = Square()
    u.world = "world"
    assert u.next_stage(u.place) is None
    t = Unit()
    t.place = u.place
    t.world = u.world
    assert u.next_stage(t) is t
    #    t.place = None
    #    assert u.next_stage(t) is None
    t.place = u.world
    u.place = t
    assert u.next_stage(t) is None
