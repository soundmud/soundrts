#! python3
from soundrts.lib import log
log.add_console_handler()

from soundrts.definitions import Rules


class RulesForDoc(Rules):

    precision_properties = ()
    precision_list_properties = ()
    string_properties = list(Rules.string_properties) + list(Rules.precision_properties)


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
    if rules.get(c, "name"):
        r = " ".join(rules.get(c, "name"))
    else:
        r = c
    if link:
        return "`" + r + "`_"
    return r

def desc(c):
    if rules.get(c, "desc"):
        return (" ".join(rules.get(c, "desc"))).replace(r"\n", "\n\n")
    else:
        return ""

def comma_join(lst, p):
    return p + " " + ", ". join(lst)

def _list(p, n, lst=None):
    if lst is None:
        lst = rules.get(c, n)
    if lst:
        return comma_join([name(_) for _ in lst], p)
    else:
        return ""

def cost(p, n):
    v = rules.get(c, n)
    if v:
        s = p
        lst = []
        if v[0]:
            lst += ["%s gold" % v[0]]
        if v[1]:
            lst += ["%s wood" % v[1]]
        return s + " " + ", ".join(lst)
    else:
        return ""

def nb(u, n):
    n = float(n)
    if isinstance(u, tuple):
        if n <= 1:
            return u[0]
        else:
            return u[1]
    if n <= 1:
        if u.endswith("s"):
            return u[:-1]
    return u

def _int(p, n, u):
    v = rules.get(c, n)
    if v:
        s = p
        s += " %s %s" % (v, nb(u, v))
        return s
    else:
        return ""

def _sint(p, n, u):
    v = rules.get(c, n)
    if v:
        s = p
        s += " %i %s" % (v, nb(u, v))
        return s
    else:
        return ""

def _res(p, n):
    v = rules.get(c, n)
    if v:
        return p + " " + ", ".join([("gold", "wood")[res] for res in rules.get(c, n)])
    else:
        return ""

def underline(s, u=","):
    return s + "\n" + u * len(s)

def kcost(c):
    r = 0
    if rules.get(c, "cost"):
        r += float(rules.get(c, "cost")[0])
        r += float(rules.get(c, "cost")[1]) * 1.01
    if not r: # special units
        r += 1000 # end of list
    return (r, name(c)) # name as a secondary key

def trained_by(c):
    r = [k for k in rules.classnames() if rules.get(k, "can_train") and c in rules.get(k, "can_train")]
    return sorted(r, key=kcost)

def can_use(c, t):
    if not rules.get(c, "can_use"):
        return []
    r = [k for k in rules.get(c, "can_use") if rules.get(k, "class") == [t]]
    return sorted(r, key=kcost)

rules = RulesForDoc()
rules.load(open("res/rules.txt", "r").read(),
           open("res/ui/rules_doc.txt", "r").read())
for cat in (("1. Units", ("worker", "soldier")),
            ("2. Buildings", ("building", )),
            ("3. Abilities", ("ability", )),
            ("4. Upgrades and research", ("upgrade", ))):
    pr(underline(cat[0], "^"))
    for c in sorted(rules.classnames(), key=kcost):
        if rules.get(c, "class")[0] not in cat[1]:
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

        if rules.get(c, "effect"):
            if rules.get(c, "effect")[0] == "bonus":
                pr("- effect: %s + %s" % (rules.get(c, "effect")[1], rules.get(c, "effect")[2]))
            elif rules.get(c, "effect")[0] == "apply_bonus":
                pr("- effect: applies the %s upgrade bonus of the unit" % rules.get(c, "effect")[1])
        pr(_int("- health: ", "hp_max", "hit points"))
        pr(_int("- health regeneration: ", "hp_regen", "hit points per second"))
        pr(_int("- armor: ", "armor", "hit points"))
        pr(_int("- armor upgrade bonus: ", "armor_bonus", "hit points"))
        if rules.get(c, "damage"):
            pr("- attack: %s every %s" % (_int("", "damage", "hit points"),
                                       _int("", "cooldown", "seconds")))
        pr(_int("- damage radius (area of effect): ", "damage_radius", "meters"))        
        pr(_int("- attack upgrade bonus: ", "damage_bonus", "hit points"))
        pr(_int("- attack range: ", "range", "meters"))
        if rules.get(c, "is_ballistic") == 1:
            pr("- can attack units located in an adjacent square if their altitude is lower (new in SoundRTS 1.2 alpha 9).")
        pr(_int("- speed: ", "speed", ("meter per second", "meters per second")))
        pr(_sint("- food provided:", "food_provided", "rations"))
        pr(_sint("- healing power:", "heal_level", ""))
        pr(_res("- can store: ", "storable_resource_types"))
        pr(_list("- can build:", "can_build"))
        pr(_list("- can train:", "can_train"))
        pr(_list("- can research:", "can_research"))
        pr(_list("- can upgrade to:", "can_upgrade_to"))
        pr(_list("- special abilities: ", None, can_use(c, "ability")))
        if rules.get(c, "bonus_height") == 1:
            pr("- have a height bonus (useful for sight and eventually attack range)")
        if rules.get(c, "is_a_detector") == 1:
            pr("- detects invisible units")
        if rules.get(c, "is_invisible") == 1:
            pr("- is invisible")
        pr(_list("- potential improvements: ", None, can_use(c, "upgrade")))
        if 0:
            try:
                pr("- combat efficiency ratio: %s (only takes into account: hit points, damage, cooldown, cost; formula: hit points * damage / cooldown / (gold cost + 3 * wood cost))" % (rules.get(c, "hp_max") * rules.get(c, "damage") / float(rules.get(c, "cooldown")) / (rules.get(c, "cost")[0] + rules.get(c, "cost")[1] * 3)))
            except:
                pass
stats = _s
