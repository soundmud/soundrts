import unittest

from commun import *


class NombreTestCase(unittest.TestCase):

    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def testNombre(self):
        self.assertEqual(nombre(1346), [3101, 3003, 3100, 3040, 3006])
        self.assertEqual(nombre(100000), [3100, 3101])
        self.assertEqual(nombre(1000000), [3001, 3102])
        self.assertEqual(nombre(1000001), [3001, 3102, 3001])
        self.assertEqual(nombre(1500000), [3001, 3102, 3005, 3100, 3101])
        self.assertEqual(nombre(1581256), [3001, 3102, 3005, 3100, 3004, 3020, 3001, 3101, 3002, 3100, 3050, 3006])


if __name__ == "__main__":
    unittest.main()
