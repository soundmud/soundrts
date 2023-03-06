from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldclient import DummyClient

tiny_map_str = """
square_width 12
nb_columns 2
nb_lines 1
nb_meadows_by_square 9
west_east_paths a1

nb_players_min 1
nb_players_max 1

player 10 10 a1 guardtower b1 peasant 
"""


def test_enter_building_from_another_square():
    w = World()
    w.load_and_build_map(Map.from_string(tiny_map_str))
    w.populate_map([DummyClient()])
    p = w.players[0]
    tower, unit = p.units

    unit.take_default_order(tower.id)
    assert unit.orders
    assert tower.orders

    w.update()
    assert not unit.orders[0].is_complete
    assert tower.orders[0].is_complete

    for _ in range(100):
        w.update()
        if unit.is_inside:
            break
    assert unit.is_inside
