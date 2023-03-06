from unittest.mock import Mock

import pytest

from soundrts.definitions import rules
from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldplayerbase import Player


@pytest.fixture()
def world():
    w = World()
    w.load_and_build_map(Map("soundrts/tests/jl1_cyclic.txt"))
    return w


@pytest.fixture()
def player(world):
    return Player(world, Mock())


def test_shortest_path(world):
    g = world.grid
    assert g["b4"].shortest_path_to(g["b1"]).other_side.place == g["b1"]
    assert g["b1"].shortest_path_to(g["b4"]).other_side.place == g["b4"]
    assert g["c2"].shortest_path_to(g["a2"]).other_side.place == g["a2"]
    assert g["a2"].shortest_path_to(g["c2"]).other_side.place == g["c2"]


def test_unit_move(world, player):
    g = world.grid
    u = rules.unit_class("peasant")(player, g["b4"], g["b4"].x, g["b4"].y)
    u.o = 0
    u.start_moving_to(g["b1"])
    u.actual_speed = u.speed
    u.action.update()
    assert u.o == 90
    for i in range(12):
        u.action.update()
    assert u.place is g["b1"]
