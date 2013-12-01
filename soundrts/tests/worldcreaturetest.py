import unittest

from servermain import *
from world import *
from worldcreature import *
from worldroom import *


class CreatureTestCase(unittest.TestCase):

    def setUp(self):
        w = Monde(Server())
        self.l = lieu(w, [], [], 0, 0, 0, 0, 100, 100)
        self.c = creature(self.l, 1, 2)
    
    def tearDown(self):
        pass

    def testCollision(self):
        self.assertEqual(self.c.collision(1, 2), False)
        c = creature(self.l, 1, 2)
        self.assertEqual(self.c.collision(1, 2), False)
        c.x, c.y = 1, 2
        self.assertEqual(self.c.collision(1, 2), True)


if __name__ == "__main__":
    unittest.main()
