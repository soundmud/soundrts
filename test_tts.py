#! python3
from __future__ import unicode_literals
from builtins import range
import time

from soundrts.lib import tts


def say(txt):
    tts.speak(txt)
    while tts.is_speaking():
        time.sleep(.01)

tts.init()
for i in range(10):
    i += 1
    say("%s " % i)
    say("This is a test. " * i)

