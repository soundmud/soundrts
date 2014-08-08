import unittest

from soundrts.definitions import rules, style
from soundrts.clientworld import order_args

rules.load("rules.txt")
style.load("ui/style.txt")


class NbArgsTestCase(unittest.TestCase):

    def testNbArgs(self):
        self.assertEqual(order_args("go", None), 1)
        self.assertEqual(order_args("patrol", None), 1)
        self.assertEqual(order_args("stop", None), 0)
        self.assertEqual(order_args("load_all", None), 1)


if __name__ == "__main__":
    unittest.main()
