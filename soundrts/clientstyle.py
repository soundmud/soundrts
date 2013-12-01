import re

from nofloat import *
from lib.log import *
from lib.defs import *


def _apply_inheritance(d, expanded_is_a=False):
    modified = True
    n = 0
    while modified:
        modified = False
        n += 1
        debug("*** pass %s ***", n)
        # for every object
        for ko, o in d.items():
            if o.has_key("is_a"):
                # init "expanded_is_a" (first pass)
                if expanded_is_a and not o.has_key("expanded_is_a"):
                    o["expanded_is_a"] = o["is_a"][:]
                    debug("%s.%s = %s", ko, "expanded_is_a", o["expanded_is_a"])
                    modified = True
                # for every parent
                for p in o["is_a"]:
                    if p in d:
                        # for every attribute
                        for k, v in d[p].items():
                            if expanded_is_a and k == "expanded_is_a":
                                # add parents from "expanded_is_a" of parent
                                # (if not yet in the object's "expanded_is_a")
                                for is_a in v:
                                    if is_a not in o[k]:
                                        o[k] += [is_a]
                                        debug("%s.%s = %s", ko, k, o[k])
                                        modified = True
                            elif k in d[p] and k not in o:
                                # copy attribute from parent
                                o[k] = v
                                debug("%s.%s = %s", ko, k, o[k])
                                modified = True
                    else:
                        warning("error in %s.is_a: %s doesn't exist", ko, p)

def _val(d, obj, attr):
    if not d.has_key(obj):
        return
    o = d[obj]
    if not o.has_key(attr):
        if o.has_key("is_a"):
            for p in o["is_a"]:
                if d.has_key(p) and _val(d, p, attr) is not None:
                    return _val(d, p, attr)
        return
    return o[attr]

def _get_from(d, obj, attr):
    v = _val(d, obj, attr)
    if v is None and attr[-8:-1] == "_level_":
        v = _val(d, obj, attr[:-8])
    if isinstance(v, list):
        v = v[:]
    return v

_style_warnings = []

def get_style(obj, attr, warn_if_not_found=True):
    result = _get_from(_style, obj, attr)
    if result is None and warn_if_not_found:
        result = [] # the caller might expect a list
        if (obj, attr) not in _style_warnings:
            _style_warnings.append((obj, attr))
            warning("no value found for %s.%s (check style.txt)", obj, attr)
    return result

def has_style(obj, attr):
    return get_style(obj, attr, False) is not None

def get_rule(obj, attr):
    return _get_from(_rules, obj, attr)

def get_style_dict(obj):
    return _style[obj]

def get_rule_dict(obj):
    return _rules[obj]

def get_style_classnames():
    return _style.keys()

def get_rule_classnames():
    result = _rules.keys()
    result.remove("parameters")
    return result

def get_ai(name):
    return _ai[name]

def get_ai_names():
    return _ai.keys()

_PRECISION_STATS = (
                "armor",
                "damage",
                "damage_radius", "range",
                "decay",
                "qty", "extraction_qty",
                "hp_max",
                "mana_cost", "mana_max",
                "extraction_time",
                "time_cost",
                "cooldown",
                "mana_regen",
                "speed", 
                )
PRECISION_STATS = []
for _ in _PRECISION_STATS:
    PRECISION_STATS.extend((_, _ + "_bonus"))
assert "armor" in PRECISION_STATS
assert "armor_bonus" in PRECISION_STATS
    
def _read_to_dict(s, d):
    s = preprocess(s)
    for line in s.split("\n"):
        words = line.split()
        if not words: continue
        if words[0] == "clear":
            d.clear()
        elif words[0] == "def":
            name = words[1]
            if name not in d:
                d[name] = {}
        elif words[0] in ("airground_type",):
            d[name][words[0]] = words[1]
        elif words[0] in (
            "collision",
            "corpse",
            "food_cost", "food_provided",
            "harm_level",
            "heal_level",
            "resource_type",
            "is_repairable", "is_healable", "is_vulnerable",
            "is_undead",
            "is_a_building_land",
            "is_buildable_anywhere",
            "special_range",
            "sight_range",
            "transport_capacity",
            "transport_volume",
            "is_invisible",
            "is_cloakable",
            "is_a_detector",
            "is_a_cloaker",
            "universal_notification",
            "presence",
            ):
            d[name][words[0]] = int(words[1])
        elif words[0] in PRECISION_STATS:
            d[name][words[0]] = to_int(words[1])
        elif words[0] in ("storable_resource_types",):
            d[name][words[0]] = [int(x) for x in words[1:]]
        elif words[0] in ("cost", "storage_bonus"):
            d[name][words[0]] = [to_int(x) for x in words[1:]]
        else:
            if words[0] == "effect" and words[1] == "bonus" and words[2] in PRECISION_STATS:
                words[3] = to_int(words[3])
                if len(words) > 4:
                    words[4] = to_int(words[4])
            d[name][words[0]] = words[1:]

def _read_ai_to_dict(s, d):
    s = preprocess(s)
    name = None
    for line in s.split("\n"):
        words = line.split()
        if not words: continue
        if words[0] == "def":
            name = words[1]
            d[name] = []
        elif name is not None:
            d[name] += [line]
        else:
            warning("'def <AI_name>' is missing (check ai.txt)")

def load_rules(*strings):
    global _rules
    _rules = {}
    for s in strings:
        _read_to_dict(s, _rules)
    _apply_inheritance(_rules, expanded_is_a=True)

def load_style(*strings):
    global _style
    _style = {}
    for s in strings:
        _read_to_dict(s, _style)
    _apply_inheritance(_style)

def load_ai(*strings):
    global _ai
    _ai = {}
    for s in strings:
        _read_ai_to_dict(s, _ai)
