import unittest

import pygame

import clientgame
from clientmedia import *
from commun import *
from clientmain import *


class GameInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        pass
##        sound_pre_init()
##        pygame.init()
##        sound_init()
##        charger_sons()
##        start_server("local")
##        self.game = clientgame.GameInterface(Server("localhost", PORT))
##        self.game.id = 1
        
    def tearDown(self):
        pass

    def testReadMsg(self):
        self.assertEqual(read_msg("[]"), ([], ""))
        self.assertEqual(read_msg("[1000]"), ([1000], ""))
        self.assertEqual(read_msg("[1000,200]"), ([1000, 200], ""))
        self.assertEqual(read_msg('[1000,"200"]'), ([1000, "200"], ""))
        self.assertEqual(read_msg('[1000,""]'), ([1000, ""], ""))
        self.assertEqual(read_msg('[1000,"joueur1"]'), ([1000, "joueur1"], ""))
        self.assertEqual(read_msg('[""]'), ([""], ""))
        self.assertEqual(read_msg('[1000,""],etc'), ([1000, ""], "etc"))
        self.assertEqual(read_msg('[1000,","],etc'), ([1000, ","], "etc"))
        self.assertRaises(ValueError, read_msg, 'a[]')
        self.assertRaises(ValueError, read_msg, '[joueur]')
        self.assertEqual(read_msg("['1000']"), (['1000'], ""))
        self.assertEqual(read_msg("[84],[],1028,-1,0,[1000],15,4,0.0,6.0,0,-1"), \
                         ([84], "[],1028,-1,0,[1000],15,4,0.0,6.0,0,-1"))

    def testEvalMsg(self):
        self.assertEqual(eval_msg('[1000,""]'), [1000, ""])
        self.assertEqual(eval_msg('[1000]'), [1000])
        self.assertRaises(ValueError, eval_msg, '[1000,""]test')
        self.assertRaises(ValueError, eval_msg, 'test[1000,""]')

    def testReadMsgAndVolume(self):
        self.assertEqual(read_msg_and_volume("[[],0.7,0.7]"), (([], 0.7, 0.7), ""))
        self.assertEqual(read_msg_and_volume("[[1000],.7,.5]"), (([1000], .7, .5), ""))
        self.assertEqual(read_msg_and_volume("[[1000,200],1,1]"), (([1000, 200], 1, 1), ""))
        self.assertEqual(read_msg_and_volume('[[1000,"200"],0,0]'), (([1000, "200"], 0, 0), ""))
        self.assertEqual(read_msg_and_volume('[[1000,""],1,1]'), (([1000, ""], 1, 1), ""))

    def testEvalMsgPart(self):
        self.assertEqual(eval_msg_part('1000'), 1000)
        self.assertEqual(eval_msg_part('"1000"'), "1000")
        self.assertRaises(ValueError, eval_msg_part, '[1000]')
        self.assertRaises(ValueError, eval_msg_part, '1000test')

    def testReadInt(self):
        self.assertEqual(read_int("1"), (1, ""))
        self.assertEqual(read_int("1,]"), (1, "]"))
        self.assertEqual(read_int("1000,200"), (1000, "200"))
        self.assertRaises(ValueError, read_int, '[1000,"200"]')

    def testReadFloat(self):
        self.assertEqual(read_float(".1"), (.1, ""))
        self.assertEqual(read_float("-1,]"), (-1, "]"))
        self.assertEqual(read_float("-1000,200"), (-1000, "200"))
        self.assertRaises(ValueError, read_float, '[1000,"200"]')


if __name__ == "__main__":
    unittest.main()
