import pytest

from soundrts import worldclient
from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldplayerhuman import Human


class DummyClient(worldclient.DummyClient):

    def push(self, *args):
        print(args)


@pytest.fixture()
def world():
    w = World([])
    w.load_and_build_map(Map("soundrts/tests/jl1_cyclic.txt"))
    return w

def test_decide_repair(world):
    g = world.grid
    place = g["a2"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, place, place.x, place.y)
    th = world.unit_class("townhall")(player, place, place.x, place.y)
    th.hp = th.hp // 2
    player.resources = [1000, 1000]
    p.decide()
    assert p.orders[0].keyword == "repair"

def test_decide_no_repair_if_no_resource(world):
    g = world.grid
    place = g["a2"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, place, place.x, place.y)
    th = world.unit_class("townhall")(player, place, place.x, place.y)
    th.hp = th.hp // 2
    player.resources = [0, 0]
    p.decide()
    assert not p.orders

def test_decide_gather_if_no_repair(world):
    g = world.grid
    place = g["a1"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, place, place.x, place.y)
    th = world.unit_class("townhall")(player, place, place.x, place.y)
    player.resources = [1000, 1000]
    p.decide()
    assert p.orders[0].keyword == "gather"
    th.hp = th.hp // 2
    p.decide()
    assert p.orders[0].keyword == "repair"
    
def test_repair_unit(world):
    g = world.grid
    place = g["a2"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, place, place.x, place.y)
    c = world.unit_class("catapult")(player, place, place.x, place.y)
    c.hp = c.hp // 2
    player.resources = [10000, 10000]
    p.decide()
    assert p.orders[0].keyword == "repair"
    assert p.orders[0].target
    for i in range(75):
        p.update()
    assert c.hp == c.hp_max

def test_high_ground_hit_chance(world):
    g = world.grid
    place = g["a1"]
    player = Human(world, DummyClient())
    a = world.unit_class("archer")(player, place, place.x, place.y)
    place2 = g["a2"]
    player2 = Human(world, DummyClient())
    a2 = world.unit_class("archer")(player2, place2, place2.x, place2.y)
    assert a.chance_to_hit(a2) == 100
    assert sum(1 for i in range(100) if a.has_hit(a2)) == 100
    place2.high_ground = True
    assert a.chance_to_hit(a2) == 50
    assert 450 < sum(1 for i in range(1000) if a.has_hit(a2)) < 550
    f = world.unit_class("footman")(player, place, place.x, place.y)
    assert f.chance_to_hit(a2) == 100 # melee
