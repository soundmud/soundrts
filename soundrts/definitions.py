import re

from nofloat import to_int
from lib.log import debug, warning
from lib.defs import preprocess


class _Definitions:

    int_properties = ()
    precision_properties = ()
    int_list_properties = ()
    precision_list_properties = ()
    string_properties = ()

    def __init__(self):
        self._dict = {}

    def read(self, s):
        s = preprocess(s)
        d = self._dict
        for line in s.split("\n"):
            words = line.split()
            if not words: continue
            if words[0] == "clear":
                d.clear()
            elif words[0] == "def":
                name = words[1]
                if name not in d:
                    d[name] = {}
            elif words[0] in self.string_properties:
                d[name][words[0]] = words[1]
            elif words[0] in self.int_properties:
                d[name][words[0]] = int(words[1])
            elif words[0] in self.precision_properties:
                d[name][words[0]] = to_int(words[1])
            elif words[0] in self.int_list_properties:
                d[name][words[0]] = [int(x) for x in words[1:]]
            elif words[0] in self.precision_list_properties:
                d[name][words[0]] = [to_int(x) for x in words[1:]]
            else:
                if words[0] == "effect" and words[1] == "bonus" and words[2] in self.precision_properties:
                    words[3] = to_int(words[3])
                    if len(words) > 4: # apparently this case doesn't happen at the moment
                        words[4] = to_int(words[4])
                d[name][words[0]] = words[1:]

    def apply_inheritance(self, expanded_is_a=False):
        d = self._dict
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

    def _val(self, obj, attr):
        d = self._dict
        if not d.has_key(obj):
            return
        o = d[obj]
        if not o.has_key(attr):
            if o.has_key("is_a"):
                for p in o["is_a"]:
                    if d.has_key(p) and self._val(p, attr) is not None:
                        return self._val(p, attr)
            return
        return o[attr]

    def get(self, obj, attr):
        d = self._dict
        v = self._val(obj, attr)
        if v is None and attr[-8:-1] == "_level_":
            v = self._val(obj, attr[:-8])
        if isinstance(v, list):
            v = v[:]
        return v

    def get_dict(self, obj):
        return self._dict[obj]

    def classnames(self):
        return self._dict.keys()

    def copy(self, other):
        self._dict = other._dict


_precision_properties = (
                "armor",
                "damage", "minimal_damage",
                "damage_radius", "range", "minimal_range",
                "decay",
                "qty", "extraction_qty",
                "hp_max",
                "mana_cost", "mana_max", "mana_start",
                "extraction_time",
                "time_cost",
                "cooldown",
                "mana_regen",
                "speed", 
                )
_precision_properties_extended = []
for _ in _precision_properties:
    _precision_properties_extended.extend((_, _ + "_bonus"))
assert "armor" in _precision_properties_extended
assert "armor_bonus" in _precision_properties_extended


class Rules(_Definitions):

    string_properties = ("airground_type",)
    int_properties = (
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
                    "bonus_height",
                    "transport_capacity",
                    "transport_volume",
                    "is_invisible",
                    "is_cloakable",
                    "is_a_detector",
                    "is_a_cloaker",
                    "universal_notification",
                    "presence",
                    "provides_survival",
                    "is_ballistic",
                    "is_teleportable",
                    "is_a_gate",
                    "is_buildable_on_exits_only",
                    "count_limit",
                    )
    precision_properties = _precision_properties_extended
    int_list_properties = ("storable_resource_types",)
    precision_list_properties = ("cost", "storage_bonus")

    def load(self, *strings):
        self._dict = {}
        for s in strings:
            s = re.sub(r"^[ \t]*class +race\b", "class faction", s, flags=re.M)
            self.read(s)
        self.apply_inheritance(expanded_is_a=True)

    def classnames(self):
        result = _Definitions.classnames(self)
        result.remove("parameters")
        return result


class Style(_Definitions):

    def __init__(self):
        self._style_warnings = []
        
    def load(self, *strings):
        self._dict = {}
        for s in strings:
            self.read(s)
        self.apply_inheritance()

    def get(self, obj, attr, warn_if_not_found=True):
        result = _Definitions.get(self, obj, attr)
        if result is None and warn_if_not_found:
            result = [] # the caller might expect a list
            if (obj, attr) not in self._style_warnings:
                self._style_warnings.append((obj, attr))
                warning("no value found for %s.%s (check style.txt)", obj, attr)
        return result

    def has(self, obj, attr):
        return self.get(obj, attr, False) is not None


# AI (probably completely separate)

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

_ai = {}

def load_ai(*strings):
    global _ai
    _ai = {}
    for s in strings:
        _read_ai_to_dict(s, _ai)

def get_ai(name):
    return _ai[name]

def get_ai_names():
    return _ai.keys()

# define two convenient variables

rules = Rules()
style = Style()
