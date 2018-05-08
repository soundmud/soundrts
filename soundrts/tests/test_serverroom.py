import time

import pytest

from soundrts.definitions import VIRTUAL_TIME_INTERVAL
from soundrts.mapfile import Map
from soundrts.serverroom import same, time_string, Game, Orders


class Client:

    def __init__(self, login):
        self.login = login

    def __repr__(self):
        return "<Client '%s'>" % self.login


clients = [Client(str(i)) for i in range(10)]


class Game(Game):

    def __init__(self, n):
        self.players = clients[:n]


def sorted_by_player(all_orders):
    return " ".join(sorted(all_orders.split()))

def test_same():
    assert same(["aaa", "aaa", "aaa"])
    assert not same(["aaa", "bbb", "aaa"])

def test_time_string():
    assert time_string("900-aaaaa") == "900"
    assert time_string("900-bbbbb") == "900"
    assert time_string("9500-aaaaa") == "9500"
    assert time_string("950aaaaa") == "950aaaaa"
    assert time_string(None) == None

def test_orders_are_ready():
    o = Orders(Game(2))
    assert not o.are_ready()
    o.add(clients[0], ("", "0-aaa"))
    assert not o.are_ready()
    o.add(clients[1], ("", "0-aaa"))
    assert o.are_ready()
    assert sorted_by_player(o.pop_and_pack()) == "0/ 1/"
    assert not o.are_ready()
    o.add(clients[0], ("", "300-aaa"))
    assert not o.are_ready()
    o.add(clients[1], ("control,24-25;order,0,0,default,7", "300-aaa"))
    assert o.are_ready()
    assert sorted_by_player(o.pop_and_pack()) == "0/ 1/control,24-25;order,0,0,default,7"

def test_orders_ignore_chronology():
    # TCP guarantees chronology.
    # Synchronisation is tested elsewhere.
    o = Orders(Game(2))
    o.add(clients[0], ("", "300-aaa"))
    assert not o.are_ready()
    o.add(clients[1], ("", "0-aaa"))
    assert o.are_ready()
    o.pop_and_pack()
    assert not o.are_ready()

def test_fpct():
    # The following values were found while using
    # localhost with Clumsy to create lag. Perhaps
    # fpct would be smaller in a real network.
    g = Game(2)
    g.real_speed = 1
    g.max_ping = 2 # instead of .3 for example
    g.ping = 0.001
    assert g.fpct() == 1
    g.ping = 0.250
    assert g.fpct() >= 2
    g.ping = 0.440
    assert g.fpct() >= 3
    g.ping = 1.040
    assert g.fpct() >= 7
    g.ping = 1.090
    assert g.fpct() >= 8

def test_short_status():
    g = Game(2)
    g.scenario = Map("soundrts/tests/jl1.txt")
    g._start_time = time.time() - 60 # 1 minute ago
    assert g.short_status == ("jl1", "0,1", 1)
    g._start_time = time.time() - .1 # a fraction of a second
    assert g.short_status[2] == 0 # not a float
