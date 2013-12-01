import re

import res


__all__ = ["nb_to_msg"]

d = None
say_one = None

def _init_dict(lang=None):
    global d, say_one
    # XXX used for the unit tests? :
##    if lang is None:
##        filename = "numbers.txt"
##    else:
##        filename = "../lang/%s/numbers.txt" % lang
    s = res.get_text("ui/numbers", locale=True) # universal newlines
    s = re.sub("(?m);.*$", "", s) # remove comments
    s = re.sub("(?m)^[ \t]*$\n", "", s) # remove empty lines
    lines = s.split("\n")
    lines = [x for x in lines if x != ""]
    say_one = map(int, lines[0].split()[1:])
    d = {}
    for line in lines[1:]:
        line = map(int, line.split())
        n, result = line[0], line[1:]
        d[n] = result

def nb_to_msg(n):
    if d is None:
        # lazy initialization (useful for testing)
        _init_dict()
    if d.has_key(n):
        if n in say_one:
            return d[1] + d[n]
        else:
            return d[n]
    else:
        msg = []
        for limit, div in ((100, 10),
                           (1000, 100),
                           (1000000, 1000),
                           (None, 1000000)):
            if limit is None or n < limit:
                a, b = divmod(n, div)
                if d.has_key(a * div):
                    msg += nb_to_msg(a * div)
                else:
                    msg += nb_to_msg(a) + d[div]
                break
        if b:
            msg += nb_to_msg(b)
        return  msg
