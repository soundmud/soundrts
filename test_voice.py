#! .venv\Scripts\python.exe
from soundrts.clientmedia import init_media
from soundrts.lib.voice import voice


def say(txt):
    voice.important([txt])


init_media()
for i in range(10):
    i += 1
    say("%s " % i)
    say("This is a test. " * i)
