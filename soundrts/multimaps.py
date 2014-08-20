import os

import config
from definitions import Style
from mapfile import Map
from paths import MAPS_PATHS
import res


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

def _move_recommended_maps(w):
    style = Style()
    style.load(res.get_text("ui/style", append=True, locale=True))
    for n in reversed(style.get("parameters", "recommended_maps")):
        for m in reversed(w[:]): # reversed so the custom map is after the official map
            if m.get_name()[:-4] == n:
                w.remove(m)
                w.insert(0, m)

def _get_worlds_multi():
    w = []
    _add_official_multi(w)
    _add_custom_multi(w)
    _move_recommended_maps(w)
    return w

_multi_maps = None
_mods = None

def worlds_multi():
    global _multi_maps, _mods
    if _multi_maps is None or _mods != config.mods:
        _multi_maps = _get_worlds_multi()
        _mods = config.mods
    return _multi_maps
