import re
from typing import Set

from .lib.defs import preprocess
from .lib.log import info, warning
from .lib.nofloat import PRECISION, to_int

VIRTUAL_TIME_INTERVAL = 300  # milliseconds
MAX_NB_OF_RESOURCE_TYPES = 10


def _update_old_definitions(d, name):
    if "sight_range" in d and d["sight_range"] == 1 * PRECISION:
        d["sight_range"] = 12 * PRECISION
        d["bonus_height"] = 1
        info(
            "in %s: replacing sight_range 1 with sight_range 12 and bonus_height 1",
            name,
        )
    if "special_range" in d:
        del d["special_range"]
        d["range"] = 12 * PRECISION
        d["minimal_range"] = 4 * PRECISION
        d["is_ballistic"] = 1
        info(
            "in %s: replacing special_range 1 with range 12, minimal_range 4 and is_ballistic 1",
            name,
        )
    return d


class _Definitions:

    int_properties: Set[str] = set()
    precision_properties: Set[str] = set()
    int_list_properties: Set[str] = set()
    precision_list_properties: Set[str] = set()
    string_properties: Set[str] = set()

    def __init__(self):
        self._dict = {}

    def read(self, s):
        s = preprocess(s)
        d = self._dict
        name = "(the name is missing)"
        for line in s.split("\n"):
            try:
                words = line.split()
                if not words:
                    continue
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
                    if words[0] == "effect_range" and len(words) >= 2:
                        if words[1] == "square":
                            words[1] = "6"
                            info(
                                "effect_range of %s will be 6 (instead of 'square')",
                                name,
                            )
                        elif words[1] == "nearby":
                            words[1] = "12"
                            info(
                                "effect_range of %s will be 12 (instead of 'nearby')",
                                name,
                            )
                        elif words[1] == "anywhere":
                            words[1] = "2147483"  # sys.maxint / 1000 (32 bits)
                    if len(words) >= 2 and words[1] == "inf":
                        words[1] = "2147483"  # sys.maxint / 1000 (32 bits)
                    d[name][words[0]] = to_int(words[1])
                elif words[0] in self.int_list_properties:
                    d[name][words[0]] = [int(x) for x in words[1:]]
                elif words[0] in self.precision_list_properties:
                    d[name][words[0]] = [to_int(x) for x in words[1:]]
                else:
                    if (
                        words[0] == "effect"
                        and words[1] == "bonus"
                        and words[2] in self.precision_properties
                    ):
                        words[3] = to_int(words[3])
                        if (
                            len(words) > 4
                        ):  # apparently this case doesn't happen at the moment
                            words[4] = to_int(words[4])
                    d[name][words[0]] = words[1:]
            except:
                warning("error in definition of %s: %s", name, line)

    def apply_inheritance(self, expanded_is_a=False):
        d = self._dict
        modified = True
        n = 0
        while modified:
            modified = False
            n += 1
            # for every object
            for ko, o in list(d.items()):
                if "is_a" in o:
                    # init "expanded_is_a" (first pass)
                    if expanded_is_a and "expanded_is_a" not in o:
                        o["expanded_is_a"] = o["is_a"][:]
                        modified = True
                    # for every parent
                    for p in o["is_a"]:
                        if p in d:
                            # for every attribute
                            for k, v in list(d[p].items()):
                                if expanded_is_a and k == "expanded_is_a":
                                    # add parents from "expanded_is_a" of parent
                                    # (if not yet in the object's "expanded_is_a")
                                    for is_a in v:
                                        if is_a not in o[k]:
                                            o[k] += [is_a]
                                            modified = True
                                elif k in d[p] and k not in o:
                                    # copy attribute from parent
                                    o[k] = v
                                    modified = True
                        else:
                            warning("error in %s.is_a: %s doesn't exist", ko, p)

    def _val(self, obj, attr):
        d = self._dict
        if obj not in d:
            return
        o = d[obj]
        if attr not in o:
            if "is_a" in o:
                for p in o["is_a"]:
                    if p in d and self._val(p, attr) is not None:
                        return self._val(p, attr)
            return
        return o[attr]

    def get(self, obj, attr):
        v = self._val(obj, attr)
        if v is None and attr[-8:-1] == "_level_":
            v = self._val(obj, attr[:-8])
        if isinstance(v, list):
            v = v[:]
        return v

    def get_dict(self, obj):
        return self._dict[obj]

    def classnames(self):
        return list(self._dict.keys())

    def copy(self, other):
        self._dict = other._dict


_precision_properties = {
    "armor",
    "damage",
    "damage_per_level",
    "minimal_damage",
    "damage_radius",
    "range",
    "minimal_range",
    "decay",
    "corpse_decay",
    "qty",
    "extraction_qty",
    "hp_max",
    "hp_max_per_level",
    "mana_cost",
    "mana_max",
    "mana_start",
    "extraction_time",
    "time_cost",
    "cooldown",
    "hp_regen",
    "hp_regen_per_level",
    "mana_regen",
    "speed",
    "effect_range",
    "effect_radius",
    "sight_range",
    "cloaking_range",
    "detection_range",
    "xp_reward_per_xp",
    "revival_time",
    "revival_time_per_level",
}
_precision_properties_extended = _precision_properties.union(
    s + "_bonus" for s in _precision_properties
)
assert "armor" in _precision_properties_extended
assert "armor_bonus" in _precision_properties_extended


class Rules(_Definitions):

    string_properties = {
        "airground_type",
    }
    int_properties = {
        "nb_of_resource_types",  # only in parameters
        "collision",
        "corpse",
        "food_cost",
        "food_provided",
        "harm_level",
        "heal_level",
        "resource_type",
        "is_repairable",
        "is_healable",
        "is_vulnerable",
        "is_undead",
        "is_a_building_land",
        "is_buildable_anywhere",
        "bonus_height",
        "inventory_capacity",
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
        "is_buildable_near_water_only",
        "count_limit",
        "global_count_limit",
        "is_revivable",
        "xp_reward",
        "xp",
        "level",
    }
    precision_properties = _precision_properties_extended
    int_list_properties = {
        "storable_resource_types",
        "xp_thresholds",
    }
    precision_list_properties = {"cost", "reward", "storage_bonus"}

    def normalize_cost_or_resources(self, lst):
        n = self.get("parameters", "nb_of_resource_types")
        while len(lst) < n:
            lst += [0]
        while len(lst) > n:
            del lst[-1]
        return lst

    def interpret(self, d, base, name):
        if hasattr(base, "interpret"):
            base.interpret(d)
        if "cost" not in d and hasattr(base, "cost"):
            d["cost"] = [0] * self.get("parameters", "nb_of_resource_types")
        d = _update_old_definitions(d, name)
        for k, v in list(d.items()):
            if k == "class":
                continue
            if (
                not hasattr(base, k)
                and not (k.endswith("_bonus") and hasattr(base, k[:-6]))
            ) or callable(getattr(base, k, None)):
                del d[k]
                warning(
                    "in %s: %s doesn't have any attribute called '%s'", name, base, k,
                )
            elif k == "cost":
                d[k] = self.normalize_cost_or_resources(v)

    def load(self, *strings, classes=()):
        self._dict = {}
        for s in strings:
            s = re.sub(r"^[ \t]*class +race\b", "class faction", s, flags=re.M)
            self.read(s)
        self.apply_inheritance(expanded_is_a=True)
        d = {}
        for k, v in self._dict.items():
            cls = v.get("class", [None])[0]
            if cls in classes:
                base = classes[cls]
                self.interpret(v, base, k)
                d[k] = type(k, (base,), v)
                d[k].type_name = k
                d[k].cls = base
        self.classes = d

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
            result = []  # the caller might expect a list
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
        if not words:
            continue
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
    return list(_ai.keys())


# define two convenient variables

rules = Rules()
style = Style()
