#! .venv\Scripts\python.exe
from soundrts.lib import log

log.add_console_handler()

import os
import os.path

from soundrts.mapfile import Map

DIR = "multi"

def size(m):
    return Map(os.path.join(DIR, m)).size()

def add_digest(m):
    p = os.path.join(DIR, m)
    return "{} {}".format(m, Map(p).get_digest())

def build():
    print("Updating list of official maps...")
    f = open("cfg/official_maps.txt", "w")
    maps = []
    for m in os.listdir(DIR):
        maps.append(m)
    maps.sort(key=size)
    f.write("\n".join([add_digest(m) for m in maps]))
    f.close()


if __name__ == "__main__":
    build()
