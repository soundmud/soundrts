import unittest


from soundrts.mapfile import *
from soundrts.world import *
from soundrts.worldclient import *


class CoordinatorTestCase(unittest.TestCase):

    def testSyncError(self):
        c = Coordinator(None, None, None, None)
        c.world = World([])
        c.world.load_and_build_map(Map("multi/m2.txt"))
        c.get_sync_debug_msg_1()
        c.get_sync_debug_msg_2()
#        print c.get_sync_debug_msg_1()
#        print c.get_sync_debug_msg_2()
        

if __name__ == "__main__":
    unittest.main()
