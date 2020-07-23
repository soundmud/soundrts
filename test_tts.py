#! .venv\Scripts\python.exe
import time

from soundrts import config
from soundrts.lib import tts


def say(txt):
    tts.speak(txt)
    while tts.is_speaking():
        time.sleep(.01)

tts.init(config.wait_delay_per_character)
for i in range(10):
    i += 1
    say("%s " % i)
    say("This is a test. " * i)

