from number import *


f = open("test_nb.txt", "w")

for r in ((0, 1000),
          (1000, 10000, 71),
          (10000, 1000000, 7771),
          (1000000, 1000000000, 777771)):
    for n in xrange(*r):
        f.write(" ".join(map(str, [n] + nb_to_msg(n))) + "\n")
