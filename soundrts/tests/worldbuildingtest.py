import unittest

#from server import *
from world import *
from worldbuilding import *
from worldplayer import *
from worldroom import *


class BuildingTestCase(unittest.TestCase):

    pass
##    def setUp(self):
##        w = RTSWorld(Server())
##        w.introduction = []
##        self.l = Zone(w, [], [], 0, 0, 0, 0, 100, 100)
##        self.p = Computer(w, DummyClient(w.server), True)
##        self.b = LumberMill(self.p, self.l, 0, 0)
##        self.h = TownHall(self.p, self.l, 0, 0)
##    
##    def tearDown(self):
##        pass
##
##    def testUpgrade(self):
##        self.p.gold = 0
##        self.p.wood = 0
##        self.b.order_upgrade_archer_weapon()
##        self.assertEqual(self.b.current_upgrade, None)
##        self.p.gold = 100
##        self.p.wood = 100
##        self.b.order_upgrade_archer_weapon()
##        self.assertNotEqual(self.b.current_upgrade, None)
##        self.assertEqual(self.b.current_upgrade[3], 60)
##        for u in range(61):
##            self.b.update()
##        self.assertEqual(self.b.current_upgrade, None)
##        self.assertEqual(self.p.gold, 100 - 8)
##        self.assertEqual(self.p.wood, 100 - 10)
##
##    def testCancelUpgrade(self):
##        self.p.gold = 100
##        self.p.wood = 100
##        self.b.order_upgrade_archer_weapon()
##        self.assertNotEqual(self.b.current_upgrade, None)
##        self.assertEqual(self.b.current_upgrade[3], 60)
##        for u in range(30):
##            self.b.update()
##        self.assertNotEqual(self.b.current_upgrade, None)
##        self.assertEqual(self.p.gold, 100 - 8)
##        self.assertEqual(self.p.wood, 100 - 10)
##        self.b.cancel_upgrading()
##        self.assertEqual(self.b.current_upgrade, None)
##        self.assertEqual(self.p.gold, 100)
##        self.assertEqual(self.p.wood, 100)
##
##    def testBuildingUpgrade(self):
##        self.p.gold = 100
##        self.p.wood = 100
##        self.assertEqual(self.h.level, 0)
##        self.h.order_upgrade_to_keep()
##        self.assertEqual(self.h.current_upgrade, None)
##        self.b = Barracks(self.p, self.l, 0, 0)
##        self.h.order_upgrade_to_keep()
##        self.assertNotEqual(self.h.current_upgrade, None)
##        self.assertEqual(self.h.current_upgrade[3], 180)
##        self.assertEqual(self.h.get_orders_txt(), [4214, 4219, 4220])
##        for u in range(181):
##            self.h.update()
##        self.assertEqual(self.h.current_upgrade, None)
##        self.assertEqual(self.h.level, 1)
##        self.assertEqual(self.p.gold, 100 - 10)
##        self.assertEqual(self.p.wood, 100 - 15)

if __name__ == "__main__":
    unittest.main()
