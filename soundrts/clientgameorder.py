from definitions import style
from lib.log import warning
from msgs import nb2msg
from nofloat import PRECISION
from worldorders import ORDERS_DICT


class OrderView(object):

    comment = []
    title = []
    index = None
    shortcut = None

    def __init__(self, model, interface=None):
        self.model = model
        self.interface = interface
        for k, v in style.get_dict(model.keyword).items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                warning("in %s: %s doesn't have any attribute called '%s'", model.keyword, self.__class__.__name__, k)

    def __getattr__(self, name):
        return getattr(self.model, name)

    @property
    def requirements_msg(self):
        and_index = 0
        msg = []
        for t in self.missing_requirements:
            and_index = len(msg)
            msg += style.get(t, "title")
        if not self.missing_requirements:
            for i, c in enumerate(self.cost):
                if c:
                    and_index = len(msg)
                    msg += nb2msg(c / PRECISION) + style.get("parameters", "resource_%s_title" % i)
            if self.food_cost:
                and_index = len(msg)
                msg += nb2msg(self.food_cost, genre="f") + style.get("parameters", "food_title")
        # add "and" if there are at least 2 requirements
        if and_index > 0:
            msg[and_index:and_index] = style.get("parameters", "and")
        if msg:
            msg[0:0] = style.get("parameters", "requires")
        return msg

    @property
    def full_comment(self):
        return self.comment + self.requirements_msg

    def title_msg(self, nb=1):
        if self.is_deferred:
            result = style.get("messages", "production_deferred")
        else:
            result = []
        result += self.title
        if self.type is not None:
            t = style.get(self.type.type_name, "title")
            if nb != 1:
                t = nb2msg(nb) + t
            result = substitute_args(result, [t])
        if self.target is not None:
            if self.keyword == "build_phase_two":
                result += style.get(self.target.type.type_name, "title")
            else:
                result += EntityView(self.interface, self.target).title
        return result

    def get_shortcut(self):
        if self.shortcut:
            return unicode(self.shortcut[0])
        if self.type and self.type.type_name:
            s = style.get(self.type.type_name, "shortcut", False)
            if s:
                return unicode(s[0])


def order_title(order):
    o = order.split()
    t = style.get(o[0], "title")
    if t is None:
        t = []
        warning("%s.title is None", o[0])
    if len(o) > 1:
        t2 = style.get(o[1], "title")
        if t2 is None:
            warning("%s.title is None", o[1])
        else:
            t = substitute_args(t, [t2])
    return t

def order_index(x):
    return _ord_index(x.split()[0])

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
    _orders_list = sorted([_x for _x in ORDERS_DICT.values()
                          if _has_ord_index(_x.keyword)],
                         key=lambda x:_ord_index(x.keyword))

def get_orders_list():
    return _orders_list

def order_comment(order, unit):
    return create_order(order, unit).full_comment

def order_args(order, unit):
    return create_order(order, unit).nb_args

def order_shortcut(order, unit):
    return create_order(order, unit).get_shortcut()

def create_order(order, unit):
    """Create Order instance from string."""
    o = order.split()
    return OrderView(ORDERS_DICT[o[0]](unit, o[1:]))

from clientworld import EntityView, substitute_args
