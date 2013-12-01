from mapfile import *


def _add_official_multi(w):
    maps = [line.strip().split() for line in open("cfg/official_maps.txt")]
    for n, digest in maps:
        p = os.path.join("multi", n)
        w.append(Map(p, digest, official=True))

def _add_custom_multi(w):
    for mp in MAPS_PATHS:
        d = os.path.join(mp, "multi")
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if os.path.normpath(p) not in (os.path.normpath(x.mapfile) for x in w):
                w.append(Map(p, None))

def _get_worlds_multi():
    w = []
    _add_official_multi(w)
    _add_custom_multi(w)
    return w

_multi_maps = None

def worlds_multi():
    global _multi_maps
    if not _multi_maps:
        _multi_maps = _get_worlds_multi()
    return _multi_maps
