from logging import *
import sys

sys.path.insert(0, "..\python")

from number import nb_to_msg, _init_dict


for lang in ("fr", "en", "de"):
    print "test " + lang
    _init_dict(lang)
    for line in open("test_nb_%s.txt" % lang):
        line = map(int, line.split())
        n, msg = line[0], line[1:]
        try:
            assert msg == nb_to_msg(n)
        except:
            print "test failed: %s => %s" % (n, msg)
            try:
                print nb_to_msg(n)
            except:
                print
                exception("")
            break
raw_input("press ENTER to exit")
