import unittest

from worldunit import *

##
##class BufferTestCase(unittest.TestCase):
##
##    def test(self):
##        b = Buffer(10, 30, 10)
##        self.assertEqual(b.qty() > 0, False)
##        b.inc()
##        self.assertEqual(b.qty() > 0, False)
##        for i in range(100):
##            b.inc()
##        self.assertEqual(b.qty() > 0, True)

##    def testInit(self):
##        o = Objective(1, [12, 13, 14])
##        self.assertEqual(o.number, 1)
##        self.assertEqual(o.description, [12, 13, 14])
##
##    def testSend(self):
##        o = Objective(1, [12, 13, 14])
###        o.send()       


##class BuildingTestCase(unittest.TestCase):
##
##    pass
##    def setUp(self):
##        w = scenario_rts_single("s1.txt", Server())
##        self.l = Zone(w, [], [], 0, 0, 0, 0, 100, 100)
##        self.p = Computer(w)
##        self.p.gold = 10000
##        self.p.wood = 10000
##    
##    def tearDown(self):
##        pass
##
##    def testAutoupdateMenusAfterBuildingCreation(self):
##        h = TownHall(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        h1 = TownHall(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        b = Barracks(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[h, h1], [h.title]])
##        self.m = LumberMill(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[b], [b.title]])
##        h.order_train_peasant()
##        self.m2 = LumberMill(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        h.order_train_peasant()
##        h.order_train_peasant()
##        h.order_train_peasant()
##        h.order_train_peasant()
##        h.cancel_training()
##        h.complete_upgrade_to_keep()
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        self.m3 = LumberMill(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        self.st = Stables(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[b], [b.title]])
##        h2 = TownHall(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        bs = Blacksmith(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[h], [h.title]])
##        bs = Blacksmith(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        b.order_train_footman()
##        b.order_train_footman()
##        b.order_train_footman()
##        b.order_train_footman()
##        b.order_train_footman()
##        self.m4 = LumberMill(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])
##        b.cancel_training()
##        self.m5 = LumberMill(self.p, self.l, 0, 0)
##        self.assertEqual(self.p._updated_u_and_c, [[], []])


if __name__ == "__main__":
    unittest.main()
