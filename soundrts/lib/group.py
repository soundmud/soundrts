from __future__ import print_function
from builtins import str
from builtins import range
def encode_range(r):
    i, j = r
    if i == j:
        return str(i)
    else:
        return "%s-%s" % (i, j)

def encode(g):
    result = [[int(i), int(i)] for i in g]
    changed = True
    while changed:
        changed = False
        prev = [None, None]
        for i, r in enumerate(result):
            if prev[1] is not None and r[0] == prev[1] + 1:
                result[i][0] = prev[0]
                del result[i - 1]
                changed = True
                break
            else:
                prev = r
    return " ".join([encode_range(r) for r in result])

def decode(s):
    if s == "":
        return []
    result = []
    for r in s.split(" "):
        if "-" in r:
            a, b = r.split("-")
            result.extend(list(range(int(a),int(b)+1)))
        else:
            result.append(int(r))
    return [str(i) for i in result]

            
if __name__ == "__main__":

    def test(a, b):
        c = encode(a)
        print('%s => "%s"' % (a, b))
        if c != b:
            print("ERROR!", c)
        if decode(encode(a)) != a:
            print("ENCODE-DECODE ERROR!")

    test(["0", "1", "2"], "0-2")
    test(["0", "1", "2"], "0-2")
    test(["0", "1", "2", "3"], "0-3")
    test(["0"], "0")
    test(["1", "2", "4"], "1-2 4")
    test(["0", "1", "2", "7", "8", "10"], "0-2 7-8 10")
    test([], "")
