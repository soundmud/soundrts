from lib import log
log.add_console_handler()

from clientstyle import *


_s = ""
"""
stats
=====

.. contents::


"""

def pr(s=""):
    global _s
    _s += s + "\n\n"

def name(c, link=True):
    if get_rule(c, "name"):
        r = " ".join(get_rule(c, "name"))
    else:
        r = c
    if link:
        return "`" + r + "`_"
    return r

def desc(c):
    if get_rule(c, "desc"):
        return (" ".join(get_rule(c, "desc"))).replace(r"\n", "\n\n")
    else:
        return ""

def comma_join(lst, p):
    return p + " " + ", ". join(lst)

def _list(p, n, lst=None):
    if lst is None:
        lst = get_rule(c, n)
    if lst:
        return comma_join([name(_) for _ in lst], p)
    else:
        return ""

def cost(p, n):
    v = get_rule(c, n)
    if v:
        s = p
        lst = []
        if v[0]:
            lst += ["%g gold" % (v[0] / PRECISION)]
        if v[1]:
            lst += ["%g wood" % (v[1] / PRECISION)]
        return s + " " + ", ".join(lst)
    else:
        return ""

def nb(u, n):
    if isinstance(u, tuple):
        if n <= 1:
            return u[0]
        else:
            return u[1]
    if n <= 1:
        if u.endswith("s"):
            return u[:-1]
    return u

def smartcvt(v, t):
#    print v, t
    if t in PRECISION_STATS:
        return "%g" % (float(v) / PRECISION)
    return "%i" % int(v) # XXX this int() shouldn't be necessary here ("effect bonus heal_level 9")

def _int(p, n, u):
    v = get_rule(c, n)
    if v:
        s = p
        s += " %g %s" % (float(v) / PRECISION, nb(u, float(v) / PRECISION))
        return s
    else:
        return ""

def _sint(p, n, u):
    v = get_rule(c, n)
    if v:
        s = p
        s += " %i %s" % (v, nb(u, v))
        return s
    else:
        return ""

def _res(p, n):
    v = get_rule(c, n)
    if v:
        return p + " " + ", ".join([("gold", "wood")[res] for res in get_rule(c, n)])
    else:
        return ""

def underline(s, u=","):
    return s + "\n" + u * len(s)

def kcost(c):
    r = 0
    if get_rule(c, "cost"):
        r += get_rule(c, "cost")[0]
        r += get_rule(c, "cost")[1] * 1.01
    if not r: # special units
        r += 1000 * PRECISION # end of list
    return (r, name(c)) # name as a secondary key

def trained_by(c):
    r = [k for k in get_rule_classnames() if get_rule(k, "can_train") and c in get_rule(k, "can_train")]
    return sorted(r, key=kcost)

def can_use(c, t):
    if not get_rule(c, "can_use"):
        return []
    r = [k for k in get_rule(c, "can_use") if get_rule(k, "class") == [t]]
    return sorted(r, key=kcost)

load_rules(open("res/rules.txt", "rU").read(),
           open("doc/rules_doc.txt", "rU").read())
for cat in (("3.2 Units", ("worker", "soldier")),
            ("3.3 Buildings", ("building", )),
            ("3.4 Abilities", ("ability", )),
            ("3.5 Upgrades and research", ("upgrade", ))):
    pr(underline(cat[0], "^"))
    for c in sorted(get_rule_classnames(), key=kcost):
        if get_rule(c, "class")[0] not in cat[1]:
            continue
        pr(underline(name(c, link=False)))
        pr(desc(c))
        pr()
        pr(_list("- trained by: ", None, trained_by(c)))
        pr(_list("- requires:", "requirements"))
        pr(_int("- mana cost:", "mana_cost", "mana points"))
        pr(cost("- total cost:", "cost"))
        pr(_sint("- total food cost:", "food_cost", "rations"))
        pr(_int("- total time cost:", "time_cost", "seconds"))

        if get_rule(c, "effect"):
            if get_rule(c, "effect")[0] == "bonus":
                pr("- effect: %s + %s" % (get_rule(c, "effect")[1],
                                          smartcvt(get_rule(c, "effect")[2], get_rule(c, "effect")[1])))
            elif get_rule(c, "effect")[0] == "apply_bonus":
                pr("- effect: applies the %s upgrade bonus of the unit" % get_rule(c, "effect")[1])
        pr(_int("- health: ", "hp_max", "hit points"))
        pr(_int("- armor: ", "armor", "hit points"))
        pr(_int("- armor upgrade bonus: ", "armor_bonus", "hit points"))
        if get_rule(c, "damage"):
            pr("- attack: %s every %s" % (_int("", "damage", "hit points"),
                                       _int("", "cooldown", "seconds")))
        pr(_int("- damage radius (area of effect): ", "damage_radius", "meters"))        
        pr(_int("- attack upgrade bonus: ", "damage_bonus", "hit points"))
        pr(_int("- attack range: ", "range", "meters"))
        pr(_int("- speed: ", "speed", ("meter per second", "meters per second")))
        pr(_sint("- food provided:", "food_provided", "rations"))
        pr(_sint("- healing power:", "heal_level", ""))
        pr(_res("- can store: ", "storable_resource_types"))
        pr(_list("- can build:", "can_build"))
        pr(_list("- can train:", "can_train"))
        pr(_list("- can research:", "can_research"))
        pr(_list("- can upgrade to:", "can_upgrade_to"))
        pr(_list("- special abilities: ", None, can_use(c, "ability")))
        if get_rule(c, "sight_range") == 1:
            pr("- can see the adjacent squares")
        if get_rule(c, "is_a_detector") == 1:
            pr("- detects invisible units")
        if get_rule(c, "is_invisible") == 1:
            pr("- is invisible")
        pr(_list("- potential improvements: ", None, can_use(c, "upgrade")))
        if 0:
            try:
                pr("- combat efficiency ratio: %s (only takes into account: hit points, damage, cooldown, cost; formula: hit points * damage / cooldown / (gold cost + 3 * wood cost))" % (get_rule(c, "hp_max") * get_rule(c, "damage") / float(get_rule(c, "cooldown")) / (get_rule(c, "cost")[0] + get_rule(c, "cost")[1] * 3)))
            except:
                pass
#        pr(str(get_rule_dict(c)))
#print _s
open("doc/src/stats.inc", "w").write(_s)
