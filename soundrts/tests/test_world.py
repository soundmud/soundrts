import unittest

from soundrts.mapfile import Map
from soundrts.world import World


class WorldTestCase(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.load_and_build_map(Map("soundrts/tests/jl1.txt"))
        self.w2 = World()
        self.w2.load_and_build_map(Map("soundrts/tests/jl2.txt"))

    def tearDown(self):
        pass

    def testShortestPath(self):
        g = self.w.grid
        self.assertEqual(
            g["a1"].shortest_path_distance_to(g["a2"]),
            g["a1"].shortest_path_distance_to(g["b1"]),
        )
        self.assertEqual(g["a1"].shortest_path_to(g["a4"]).other_side.place.name, "a2")
        self.assertEqual(g["b1"].shortest_path_to(g["c2"]).other_side.place.name, "c1")
        self.assertEqual(g["b1"].shortest_path_to(g["a3"]).other_side.place.name, "a1")
        g2 = self.w2.grid
        self.assertEqual(g2["a1"].shortest_path_to(g2["c1"]), None)
        self.assertEqual(g2["c1"].shortest_path_to(g2["a1"]), None)

    def testCheckString(self):
        World().get_digest()
        self.assertEqual(self.w.get_digest(), self.w.get_digest())
        self.assertNotEqual(self.w.get_digest(), self.w2.get_digest())
        self.w.get_objects_string()


#        print self.w.get_objects_string()[-160:]


if __name__ == "__main__":
    unittest.main()
