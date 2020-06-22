from typing import List

from .definitions import style, rules
from .lib.log import warning
from .lib.msgs import nb2msg
from .lib.nofloat import PRECISION
from . import msgparts as mp
from .worldorders import ORDERS_DICT


def nb2msg_f(n):
    # the TTS cannot guess how to say "1 ration" ("une ration")
    # (note: many other cases are not correctly done)
    if n == 1:
        return mp.ONE_F
    return nb2msg(n)


class OrderTypeView: # future order

    type = None
    requirements: List[str] = []

    def __init__(self, order, unit):
        self.unit = unit
        o = order.split()
        self.cls = ORDERS_DICT[o[0]]
        if len(o) > 1:
            self.type = o[1]
            self.requirements = self.unit.player.world.unit_class(self.type).requirements
        self.title = self._get_title()
        self.shortcut = self._get_shortcut()
        self.index = _ord_index(self.cls.keyword)

        self.comment = style.get(self.cls.keyword, "comment", False)
        if self.comment is None: self.comment = []

        self.cost = self.cls(unit, [self.type]).cost
        self.food_cost = self.cls(unit, [self.type]).food_cost
        self.nb_args = self.cls.nb_args

    def __eq__(self, other):
        return self.cls.keyword == other.cls.keyword and self.type == other.type

    def _get_title(self):
        t = style.get(self.cls.keyword, "title")
        if t is None:
            t = []
            warning("%s.title is None", self.cls.keyword)
        if self.type:
            t2 = style.get(self.type, "title")
            if t2 is None:
                warning("%s.title is None", self.type)
            else:
                t = substitute_args(t, [t2])
        return t

    def _get_shortcut(self):
        s = style.get(self.cls.keyword, "shortcut", False)
        if s:
            return str(s[0])
        if self.type:
            s = style.get(self.type, "shortcut", False)
            if s:
                return str(s[0])

    def _get_requirements_msg(self):
        and_index = 0
        msg = []
        missing = [r for r in self.requirements if not self.unit.player.has(r)]
        for t in missing:
            and_index = len(msg)
            msg += style.get(t, "title")
        if not missing:
            if self.cost:
                for i, c in enumerate(self.cost):
                    if c:
                        and_index = len(msg)
                        msg += nb2msg(c / PRECISION) + style.get("parameters", "resource_%s_title" % i)
            if self.food_cost:
                and_index = len(msg)
                msg += nb2msg_f(self.food_cost) + style.get("parameters", "food_title")
        # add "and" if there are at least 2 requirements
        if and_index > 0:
            msg[and_index:and_index] = style.get("parameters", "and")
        if msg:
            msg[0:0] = style.get("parameters", "requires")
        return msg

    @property
    def full_comment(self):
        return self.comment + self._get_requirements_msg()

    @property
    def encode(self):
        result = self.cls.keyword
        if self.type:
            result += " " + self.type
        return result        


def _ord_index(keyword):
    try:
        return float(style.get(keyword, "index")[0])
    except:
        warning("%s.index should be a number (check style.txt)", keyword)
        return 9999 # end of the list

def _has_ord_index(keyword):
    return style.has(keyword, "index")

_orders_list = ()

def update_orders_list():
    global _orders_list
    # this sorted list of order classes is used when generating the menu
    _orders_list = sorted([_x for _x in list(ORDERS_DICT.values())
                          if _has_ord_index(_x.keyword)],
                         key=lambda x:_ord_index(x.keyword))

def get_orders_list():
    return _orders_list

def substitute_args(t, args):
    if t is not None:
        while "$1" in t:
            i = t.index("$1")
            del t[i]
            t[i:i] = args[0]
        return t
