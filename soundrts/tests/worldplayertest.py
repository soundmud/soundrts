import unittest

from soundrts.commun import PRECISION
from soundrts import worldclient
from soundrts.multimaps import worlds_multi
###from server import *
from soundrts.world import *
##from worldbuilding import *
from soundrts.worldplayer import *
##from worldroom import *


class ObjectiveTestCase(unittest.TestCase):

    def testInit(self):
        o = Objective(1, [12, 13, 14])
        self.assertEqual(o.number, 1)
        self.assertEqual(o.description, [12, 13, 14])

    def testSend(self):
        o = Objective(1, [12, 13, 14])
#        o.send()       


##class _DummyWorld:
##
##    def get_next_player_number(self): return 0
##    def get_next_id(self): return 0
##    introduction = []


class DummyClient(worldclient.DummyClient):

    def push(self, txt):
        if False: # remove this to check the values
            print txt
 

class ComputerTestCase(unittest.TestCase):

##    def set_up(self):
##        w = World([])
##        w.introduction = []
##        w.load_and_build_map(worlds_multi()[0])
##        cl = _DummyClient()
##        cp = Computer(w, cl, False)
##        w.players_starts[0][1].append(("b1", w.unit_class("new_flyingmachine")))
##        w.players_starts[0][1].append(("b1", w.unit_class("castle")))
###        print w.players_starts[0][1]
##        cp.init_position(w.players_starts[0])
##        self.cp2 = Computer(w, cl, False)
##        self.cp2.init_position(w.players_starts[1])
##        return w, cl, cp

    def set_up(self, alliance=(1, 2), cloak=False):
        w = World([])
        w.introduction = []
        w.load_and_build_map(worlds_multi()[0])
        w.players_starts[0][1].append(("b1", w.unit_class("new_flyingmachine")))
        w.players_starts[0][1].append(("b1", w.unit_class("flyingmachine")))
        w.players_starts[0][1].append(("b1", w.unit_class("dragon")))
        w.players_starts[0][1].append(("b1", w.unit_class("castle")))
        w.players_starts[1][1].append(("b4", w.unit_class("new_flyingmachine")))
        w.players_starts[1][1].append(("b4", w.unit_class("flyingmachine")))
        w.players_starts[1][1].append(("b4", w.unit_class("dragon")))
        w.players_starts[1][1].append(("b4", w.unit_class("castle")))
        if cloak:
            w.unit_class("new_flyingmachine").dct["is_a_cloaker"] = True
        cl = DummyClient()
        cl2 = DummyClient()
        w.populate_map([cl, cl2], alliance)
        cp, self.cp2 = w.players
        return w, cl, cp

    def find_player_unit(self, p, cls_name):
        for u in p.units:
            if u.type_name == cls_name:
                return u

    def testInitAndGetAPeasant(self):
        w, cl, cp = self.set_up()
        assert sorted(w.get_makers("peasant")) == ["castle", "keep", "townhall"]
        assert sorted(w.get_makers("footman")) == ["barracks"]
        assert sorted(w.get_makers("barracks")) == ["peasant"]
        th = self.find_player_unit(cp, "townhall")
        assert not th.orders
        assert not cp.get(1000, "peasant")
        assert th.orders

    def testInitAndGetAFootman(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        assert not p.orders
        assert not cp.get(1000, "footman")
        assert p.orders

    def testInitAndUpgradeToAKeep(self):
        w, cl, cp = self.set_up()
        cp.resources = [1000*PRECISION, 1000*PRECISION]
        th = self.find_player_unit(cp, "townhall")
        assert not th.orders
        assert not cp.get(1, "keep")
        assert not th.orders
        cp.lang_add_units(["a1", "barracks"])
        assert self.find_player_unit(cp, "barracks")
        assert not cp.get(1, "knight") # => get keep
        assert th.orders

    def testMenace(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        assert p.menace > 0
        th = self.find_player_unit(cp, "townhall")
        assert th.menace == 0

    def testImmediateOrder(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        p.take_order(["go", 1])
        assert p.orders
        p.take_order(["mode_offensive"])
        assert p.orders

    def testPerception(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        assert p.player.is_perceiving(p)
        p2 = self.find_player_unit(self.cp2, "peasant")
        p2place = p2.place
        assert not p.player.is_perceiving(p2)
        assert not p.place in p2.player.observed_before_squares
        p2.move_to(p.place)
        assert p.player.is_perceiving(p2)
        assert p2.player.is_perceiving(p)
        assert p.place in p2.player.observed_before_squares
        fm = self.find_player_unit(cp, "new_flyingmachine")
        assert not p.is_inside
        fm.load(p)
        assert p.is_inside
        assert not p2.player.is_perceiving(p)
        fm.unload_all()
        assert not p.is_inside
        assert p2.player.is_perceiving(p)
        p2.move_to(p2place)
        assert not p.player.is_perceiving(p2)
        assert not p2.player.is_perceiving(p)
        p2.move_to(p.place)
        assert p.player.is_perceiving(p2)
        assert p2.player.is_perceiving(p)
        p2.die()
        assert not self.cp2.is_perceiving(p)
        fm.load_all()
        fm.unload_all()
        fm.load_all()
        fm.unload_all()

    def testPerceptionAfterUnitDeath(self):
        w, cl, cp = self.set_up()
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        assert cp.is_perceiving(p)
        assert p in cp.perception
        assert p not in [_.initial_model for _ in cp.memory]
        p2 = self.find_player_unit(cp2, "peasant")
        assert p2 not in [_.initial_model for _ in cp.memory]
        assert p2 not in cp.perception
        p.move_to(p2.place)
        assert cp.is_perceiving(p)
        assert p in cp.perception
        th2 = self.find_player_unit(cp2, "townhall")
        assert th2 in cp.perception
        p.die()
        assert th2 not in cp.perception
        assert th2 in [_.initial_model for _ in cp.memory]
        assert not cp.is_perceiving(p)
        assert p not in cp.perception
        assert p not in [_.initial_model for _ in cp.memory]

    def testPerceptionAfterUnitOwnershipChange(self):
        w, cl, cp = self.set_up()
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        assert cp.is_perceiving(p)
        assert p in cp.perception
        assert p not in [_.initial_model for _ in cp.memory]
        p2 = self.find_player_unit(cp2, "peasant")
        assert p2 not in [_.initial_model for _ in cp.memory]
        assert p2 not in cp.perception
        p.move_to(p2.place)
        assert cp.is_perceiving(p)
        assert p in cp.perception
        th2 = self.find_player_unit(cp2, "townhall")
        assert th2 in cp.perception
        p.set_player(None)
        assert th2 not in cp.perception
        assert th2 in [_.initial_model for _ in cp.memory]
        assert not cp.is_perceiving(p)
        assert p not in cp.perception
        assert p in [_.initial_model for _ in cp.memory]

    def testMemoryOfResourceWhenAlliance(self):
        w, cl, cp = self.set_up((1, 1))
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        assert p.player.is_perceiving(p)
        assert cp2.is_perceiving(p)
        initial = p.place
        for o in w.grid["a2"].objects:
            assert not p.player.is_perceiving(o)
            assert not cp2.is_perceiving(o)
            assert o not in [_.initial_model for _ in p.player.memory]
            assert o not in p.player.perception
            assert o not in cp2.perception
        p.move_to(w.grid["a2"])
        for o in w.grid["a2"].objects:
            assert p.player.is_perceiving(o)
            assert cp2.is_perceiving(o)
            assert o not in [_.initial_model for _ in p.player.memory]
            assert o in p.player.perception
            assert o in cp2.perception
        p.move_to(initial)
        for o in w.grid["a2"].objects:
            assert not p.player.is_perceiving(o)
            assert not cp2.is_perceiving(o)
            assert o not in p.player.perception
            assert o not in cp2.perception
            assert o in [_.initial_model for _ in p.player.memory]

    def testHas(self):
        w, cl, cp = self.set_up()
        c = self.find_player_unit(cp, "castle")
        assert cp.has("castle")
        assert cp.has("keep")
        assert cp.has("townhall")
        th = self.find_player_unit(cp, "townhall")
        th.delete()
        assert cp.has("castle")
        assert cp.has("keep")
        assert cp.has("townhall")
        c.delete()
        assert not cp.has("castle")
        assert not cp.has("keep")
        assert not cp.has("townhall")

    def testHas2(self):
        w, cl, cp = self.set_up()
        c = self.find_player_unit(cp, "castle")
        assert cp.has("castle")
        assert cp.has("keep")
        assert cp.has("townhall")
        th = self.find_player_unit(cp, "townhall")
        c.delete()
        assert not cp.has("castle")
        assert not cp.has("keep")
        assert cp.has("townhall")

    def testReact(self):
        w, cl, cp = self.set_up()
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        p2 = self.find_player_unit(cp2, "peasant")
        self.assertTrue(p2.is_an_enemy(p))
        p.move_to(p2.place)
        self.assertTrue(p2.can_attack(p)) # (a bit too late to test this)
        self.assertEqual(p2.cible, p) # "peasant should attack peasant"

    def testUpgradeTo(self):
        w, cl, cp = self.set_up()
        th = self.find_player_unit(cp, "townhall")
        cp.lang_add_units([th.place.name, "barracks"])
        self.assertEqual(cp.nb("keep"), 0)
        self.assertEqual(cp.nb("barracks"), 1)
        cp.resources = [100000, 100000]
        th.take_order(["upgrade_to", "keep"])
        assert th.orders
        self.assertFalse(th.orders[0].is_impossible)
        for _ in range(10000):
            th.update()
            if not th.orders:
                break
        assert not th.orders
        self.assertEqual(cp.nb("keep"), 1)
        self.assertEqual(th.place, None)
        self.assertTrue(th not in cp.units, "townhall still belongs to the player")

    def testAllied(self):
        # when allied
        w, cl, cp = self.set_up((1, 1), cloak=True)
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        p2 = self.find_player_unit(cp2, "peasant")
        th = self.find_player_unit(cp, "townhall")
        # allied: hostility
        self.assertFalse(p.is_an_enemy(p2))
        self.assertFalse(cp.is_an_enemy(cp2))
        # allied_vision
        self.assertTrue(cp.is_perceiving(p2))
        # allied: heal
        th.heal_level = 1 # force healing by the townhall (only the priest heals now)
        p2.hp = 0
        p2.move_to(p.place)
        for _ in range(1):
            th.update()
            th.slow_update()
            if p2.hp > 0:
                break
        assert p2.hp > 0
        # allied: cloak
        self.assertTrue(p.is_invisible_or_cloaked())
        self.assertTrue(p2.is_invisible_or_cloaked())
        # allied_victory
        self.assertTrue(cp.lang_no_enemy_left(None))

    def testAllied2(self):
        # when not allied
        w, cl, cp = self.set_up(cloak=True)
        cp2 = self.cp2
        p = self.find_player_unit(cp, "peasant")
        p2 = self.find_player_unit(cp2, "peasant")
        th = self.find_player_unit(cp, "townhall")
        # allied: hostility
        self.assertTrue(p.is_an_enemy(p2))
        self.assertTrue(cp.is_an_enemy(cp2))
        # allied_vision
        self.assertFalse(cp.is_perceiving(p2))
        # allied: heal
        p2.hp = 0
        p2.move_to(p.place)
        for _ in range(1):
            th.update()
            th.slow_update()
            if p2.hp > 0:
                break
        assert p2.hp == 0
        # allied: cloak
        self.assertTrue(p.is_invisible_or_cloaked())
        self.assertFalse(p2.is_invisible_or_cloaked())
        # allied_victory
        self.assertFalse(cp.lang_no_enemy_left(None))

    def testAI(self):
        w, cl, cp = self.set_up()
        th = self.find_player_unit(cp, "townhall")
        self.assertEqual(cp.nearest_warehouse(th.place, 0), th)
        self.assertEqual(cp.nearest_warehouse(th.place, 1), th)
        self.assertEqual(th.place.shortest_path_distance_to(th.place), 0)

    def testImperativeGo(self):        
        w, cl, cp = self.set_up()
        th = self.find_player_unit(cp, "townhall")
        p = self.find_player_unit(cp, "peasant")
        p.take_order(["go", th.id], imperative=True)
        self.assertEqual(th.hp, th.hp_max)
        for _ in range(100):
            p.update()
            if th.hp != th.hp_max:
                break
        self.assertNotEqual(th.hp, th.hp_max)

    def testImperativeGo2(self):        
        w, cl, cp = self.set_up()
        th = self.find_player_unit(cp, "townhall")
        f = self.find_player_unit(cp, "flyingmachine")
        f.take_order(["go", th.id], imperative=True)
        self.assertEqual(th.hp, th.hp_max)
        for _ in range(100):
            f.update()
            if th.hp != th.hp_max:
                break
        self.assertNotEqual(th.hp, th.hp_max)

    def testImperativeGo3(self):        
        w, cl, cp = self.set_up()
        th = self.find_player_unit(cp, "townhall")
        f = self.find_player_unit(cp, "dragon")
        f.take_order(["go", th.id], imperative=True)
        self.assertEqual(th.hp, th.hp_max)
        for _ in range(100):
            f.update()
            if th.hp != th.hp_max:
                break
        self.assertNotEqual(th.hp, th.hp_max)

    def testMoveSlowly(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        p.speed /= 100
        p.move_to(w.grid["a2"])
        p.take_order(["go", w.grid["a1"].id])
        x, y = p.x, p.y
        w.update() # for the order
        assert (x, y) == (p.x, p.y) # XXX not important
        w.update() # move
        assert (x, y) != (p.x, p.y)
        x2, y2 = p.x, p.y
        assert (x2, y2) == (p.x, p.y)

        # do this a second time => same result
        p.move_to(w.grid["a2"], x, y)
        assert (x, y) == (p.x, p.y)
        p.cible = None
        p.take_order(["go", w.grid["a1"].id])
        assert (x, y) == (p.x, p.y)
        w.update() # for the order
        assert (x, y) == (p.x, p.y) # XXX not important
        w.update() # move
        assert (x, y) != (p.x, p.y)
        assert (x2, y2) == (p.x, p.y)

        # without collision => same result
        w.collision[p.airground_type].remove(p.x, p.y)
        p.collision = 0
        p.move_to(w.grid["a2"], x, y)
        assert (x, y) == (p.x, p.y)
        p.cible = None
        p.take_order(["go", w.grid["a1"].id])
        assert (x, y) == (p.x, p.y)
        w.update() # for the order
        assert (x, y) == (p.x, p.y) # XXX not important
        w.update() # move
        assert (x, y) != (p.x, p.y)
        assert (x2, y2) == (p.x, p.y)

    def testDieToAirTransport(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        f = self.find_player_unit(cp, "new_flyingmachine")
        pl = f.place
        f.load(p)
        f.die()
        assert isinstance(pl.objects[-1], Corpse)
        assert pl.objects[-1].unit.type_name == "peasant"
        assert not p.place is pl

    def testSurviveToGroundTransport(self):
        w, cl, cp = self.set_up()
        p = self.find_player_unit(cp, "peasant")
        f = self.find_player_unit(cp, "new_flyingmachine")
        pl = f.place
        f.airground_type = "ground"
        f.load(p)
        f.die()
        assert not isinstance(pl.objects[-1], Corpse)
        assert p.place is pl


class BuildingTestCase(unittest.TestCase):

    pass
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


class PlayerBaseTestCase(unittest.TestCase):

    def set_up(self, alliance=(1, 2), cloak=False):
        w = World([])
        w.introduction = []
        w.load_and_build_map(worlds_multi()[0])
        w.players_starts[1][1].append(("b4", w.unit_class("lumbermill")))
        cl = DummyClient()
        cl2 = DummyClient()
        w.populate_map([cl, cl2], alliance)
        cp, self.cp2 = w.players
        return w, cl, cp

    def testStorageBonus(self):
        w, cl, cp = self.set_up()
        cp2 = self.cp2
        w.update()
        assert sorted((cp.storage_bonus[1], cp2.storage_bonus[1])) \
               == [0, 1 * PRECISION]


if __name__ == "__main__":
    unittest.main()
