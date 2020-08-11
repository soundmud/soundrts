import glob
import re

r = set()
for n in glob.glob("soundrts/*.py") + glob.glob("soundrts/lib/*.py"):
    s = open(n).read()
    r.update(re.findall(r"mp\.(\w+)", s))
print(len(r), "message part constants used")
m = set(re.findall(r"^\w+", open("soundrts/msgparts.py").read(), flags=re.M))
print(len(m), "message part constants defined")
print("undefined:", " ".join(r - m))
print("unused:", " ".join(m - r))
