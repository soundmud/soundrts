import pytest

from soundrts.mapfile import Map
from soundrts.world import World
from soundrts import worldclient
from soundrts.worldplayerhuman import Human


class DummyClient(worldclient.DummyClient):

    def push(self, *args):
        print(args)


@pytest.fixture()
def world():
    w = World([])
    w.load_and_build_map(Map("soundrts/tests/height.txt"))
    return w

def test_must_not_see_plateau_from_below_even_if_path_exists(world):
    g = world.grid
    a1 = g["a1"]  # plateau
    b1 = g["b1"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, b1, b1.x, b1.y)
    assert a1 not in p.get_observed_squares(partial=True)

def test_must_see_diagonal_if_path_exists(world):
    g = world.grid
    a2 = g["a2"]
    b1 = g["b1"]
    player = Human(world, DummyClient())
    p = world.unit_class("peasant")(player, b1, b1.x, b1.y)
    assert a2 in p.get_observed_squares(partial=True)
