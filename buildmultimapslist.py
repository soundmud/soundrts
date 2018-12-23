#! python2.7
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
    return "%s %s" % (m, Map(p).get_digest())


f = open("cfg/official_maps.txt", "w")
maps = []
for m in os.listdir(DIR):
    if m != "list.txt": # XXX not necessary
        maps.append(m)
maps.sort(key=size)
f.write("\n".join([add_digest(m) for m in maps]))
f.close()
