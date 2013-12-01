import unittest

import pygame

from clientmedia import *


class VoiceTestCase(unittest.TestCase):

    def setUp(self):
        sound_pre_init()
        pygame.init()
        sound_init()
        voice.init()
#        charger_sons()
    
    def tearDown(self):
        pass

    def testInit(self):
        voice.update()
        voice.info([])
        voice.flush()


if __name__ == "__main__":
    unittest.main()
