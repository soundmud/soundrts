import random

from soundrts.lib.nofloat import PRECISION
from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldclient import DummyClient
from soundrts.worldplayercomputer import Computer

tiny_map_str = """
square_width 12
nb_columns 1
nb_lines 1
nb_meadows_by_square 9
goldmine 1000 a1

nb_players_min 1
nb_players_max 1
starting_squares a1
starting_units townhall farm peasant
starting_resources 10 10
"""
tiny_map2_str = """
square_width 12
nb_columns 3
nb_lines 1
nb_meadows_by_square 18
goldmine 1000 a1 c1
wood 1000 a1 c1
west_east_paths a1 b1

nb_players_min 2
nb_players_max 2
starting_squares a1 c1
starting_units townhall farm peasant
starting_resources 10 10
"""


def get_map(s):
    m = Map()
    m.map_string = s
    m.path = ""
    return m


def time_to_500_gold(nb_workers):
    Computer.nb_workers_to_get = nb_workers
    w = World([])
    w.load_and_build_map(get_map(tiny_map_str))
    c = DummyClient(AI_type="aggressive")
    w.populate_map([c])
    p = w.players[0]
    dt = 3 * 60
    for i in range(dt * 20):
        # if i % dt == 0:
        #     print(i // dt, "minutes",
        #           "gold:", p.resources[0] // PRECISION,
        #           "workers:", len(list(filter(lambda x: x.type_name == "peasant", p.units))))
        w.update()
        if p.resources[0] > 500 * PRECISION:
            return i / dt


def computer_vs_computer(nb_workers):
    w = World([], seed=random.randint(0, 100000))
    w.load_and_build_map(get_map(tiny_map2_str))
    c = DummyClient(AI_type="aggressive")
    c.alliance = 9
    c2 = DummyClient(AI_type="aggressive")
    w.populate_map([c, c2])
    p, p2 = w.players
    p.nb_workers_to_get = nb_workers
    dt = 3 * 60
    for i in range(dt * 60):
        w.update()
        if i % dt == 0:
            print(len(p.units), len(p2.units))
            # print(p.units)
            # print(p2.units)
        if not p.units:
            return "loss", i
        if not p2.units:
            return "win", i
    return "draw", i


def test1():
    for n in range(30):
        print(n, time_to_500_gold(n))


n = 0
for _ in range(10):
    win, t = computer_vs_computer(15)
    print(win)
    if win == "win":
        n += 1
print(n, "wins /", 10)
