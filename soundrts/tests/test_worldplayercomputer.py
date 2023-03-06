from soundrts.world import World
from soundrts.worldclient import DummyClient
from soundrts.worldplayercomputer import Computer
from soundrts.worldresource import Deposit
from soundrts.worldroom import Square


class Deposit(Deposit):  # type: ignore
    def __init__(self, type_):
        self.resource_type = type_


class Warehouse:
    def __init__(self, types):
        self.storable_resource_types = types


def test_is_ok_for_warehouse():
    w = World()
    c = Computer(w, DummyClient())
    a1 = Square(w, 0, 0, 12)
    assert a1.name == "a1"
    assert not c.is_ok_for_warehouse(a1, 0)
    a1.objects.append(Deposit(0))
    assert c.is_ok_for_warehouse(a1, 0)
    a1.objects.append(Warehouse([1]))
    assert c.is_ok_for_warehouse(a1, 0)
    a1.objects.append(Warehouse([0]))
    assert not c.is_ok_for_warehouse(a1, 0)
