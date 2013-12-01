import unittest

from servermain import *
from world import *
from worldresource import *
from worldroom import *


class ResourceTestCase(unittest.TestCase):

    def setUp(self):
        w = RTSWorld(Server())
        self.l = Zone(w, [], [], 0, 0, 0, 0, 100, 100)
        self.w = Wood(self.l, 0, 0)
    
    def tearDown(self):
        pass

    def testDescription(self):
        self.assertEqual(self.w.description, [134] + nombre(75) + [132])


if __name__ == "__main__":
    unittest.main()
