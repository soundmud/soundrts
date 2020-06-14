from builtins import range
import pytest

from soundrts.mapfile import Map
from soundrts.world import World


class Player:
    food = 0
    nb_units_produced = 0
    used_food = 0
    
    def __init__(self):
        self.allied_vision = [self]
        self.perception = set()
        self.units = []


@pytest.fixture()
def world():
    w = World([])
    w.load_and_build_map(Map("soundrts/tests/jl1_cyclic.txt"))
    return w

def test_shortest_path(world):
    g = world.grid
    assert g["b4"].shortest_path_to(g["b1"]).other_side.place == g["b1"]
    assert g["b1"].shortest_path_to(g["b4"]).other_side.place == g["b4"]
    assert g["c2"].shortest_path_to(g["a2"]).other_side.place == g["a2"]
    assert g["a2"].shortest_path_to(g["c2"]).other_side.place == g["c2"]

def test_unit_move(world):
    g = world.grid
    u = world.unit_class("peasant")(Player(), g["b4"], g["b4"].x, g["b4"].y)
    u.o = 0
    u.start_moving_to(g["b1"])
    u.actual_speed = u.speed
    u.action.update()
    assert u.o == 90
    for i in range(12):
        u.action.update()
    assert u.place is g["b1"]
