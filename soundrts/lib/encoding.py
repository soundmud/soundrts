# http://www.python.org/dev/peps/pep-0263/

import re


def encoding(text):
    result = _encoding(text.split("\n"))
    if result is None:
        result = "latin_1"
    return result

def _encoding(lines):
    for n, line in enumerate(lines):
        if n == 0 and line.startswith("\xef\xbb\xbf"):
            return "utf-8"
        if n > 1:
            break
        m = re.search(r"coding[:=]\s*([-\w.]+)", line)
        if m is not None:
            return m.group(1)


if __name__ == "__main__":
    assert _encoding(("; coding: big5\n", )) == "big5"
    assert _encoding(("; coding: latin_1\n", )) == "latin_1"
    assert _encoding(("; coding: latin-1\n", )) == "latin-1"
    assert _encoding(("; test\n", "; coding: big5\n")) == "big5"
    assert _encoding((";", "; test\n", "; coding: big5\n")) is None
    assert _encoding(("; coding: big5\n", )) == "big5"
    assert _encoding(("; encoding: big5\n", )) == "big5"
    assert _encoding(("# -*- coding: big5 -*-", )) == "big5"
    assert _encoding(("# vim: set fileencoding=big5 :", )) == "big5"
    assert _encoding(("\xef\xbb\xbf; coding: big5\n", )) == "utf-8"
