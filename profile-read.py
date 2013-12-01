import os
import os.path
import pstats
import sys

n = os.path.join(os.environ["TMP"], "clientprof")
if not os.path.exists(n):
    sys.exit()

nb = 1
while True:
    f = "profiles/profile%s.txt" % nb
    if not os.path.exists(f):
        break
    nb += 1
sys.stdout = open(f, "w")

p = pstats.Stats(n)
#p.sort_stats('time').print_stats(20)
p.sort_stats('time', 'cum').print_stats(30)
p.print_callers(30)
p.print_callees(20)
p.sort_stats('cumulative').print_stats(50)
os.rename(n, "profiles/clientprof%s" % nb)
#os.remove(n) # remove file to avoid potential problems if rewriting is not done
#raw_input("[ENTER to quit]")
