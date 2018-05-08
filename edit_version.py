#! python3
V, N, P = "version.txt", "version-name.txt", "soundrts/version.py"
version = open(V).read()
name = open(N).read()
if version not in open(P).read():
    print(f"fix the version name in '{P}' first.")
else:
    v = input(f"new version (was '{version}')? ")
    if not v:
        v = version
    n = input(f"new version name (was '{name}')? ")
    if not n:
        n = name
    open(V, "w").write(v)
    open(N, "w").write(n)
    s = open(P).read().replace(version, v, 1)
    open(P, "w").write(s)
    print("OK")
input("press ENTER to quit")
