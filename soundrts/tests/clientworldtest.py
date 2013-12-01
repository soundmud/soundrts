import unittest

from clientstyle import *
from clientworld import *

load_rules("rules.txt")
load_style("ui/style.txt")

class NbArgsTestCase(unittest.TestCase):

    def testNbArgs(self):
        self.assertEqual(order_args("go", None), 1)
        self.assertEqual(order_args("patrol", None), 1)
        self.assertEqual(order_args("stop", None), 0)
##        self.assertEqual(order_args("use a_teleportation", None), 1)
##        self.assertEqual(order_args("use a_conversion", None), 1)
##        self.assertEqual(order_args("use a_summon", None), 0)
##        self.assertEqual(order_args("build farm", None), 1)
##        self.assertEqual(order_args("train peasant", None), 0)
        self.assertEqual(order_args("load_all", None), 1)

if __name__ == "__main__":
    unittest.main()
