import unittest

from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldclient import Coordinator


class CoordinatorTestCase(unittest.TestCase):
    def testSyncError(self):
        c = Coordinator(None, None, None)
        c.world = World([])
        c.world.load_and_build_map(Map("multi/m2.txt"))
        c.world.update()
        c.get_sync_debug_msg_1()
        c.get_sync_debug_msg_2()
        c.world.update()
        c.get_sync_debug_msg_1()
        c.get_sync_debug_msg_2()


#        print c.get_sync_debug_msg_1()
#        print c.get_sync_debug_msg_2()


def test_nb_players_after_unpack():
    for n in ["jl1.txt", "jl4"]:
        m = Map(unpack=Map(f"multi/{n}").pack())
        assert m.nb_players_min == 2


if __name__ == "__main__":
    unittest.main()
