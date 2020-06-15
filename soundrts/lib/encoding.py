# http://www.python.org/dev/peps/pep-0263/

import re


def encoding(text):
    result = _encoding(text.split(b"\n"))
    if result is None:
        result = "latin_1"
    return result

def _encoding(lines):
    for n, line in enumerate(lines):
        if n == 0 and line.startswith(b"\xef\xbb\xbf"):
            return "utf-8"
        if n > 1:
            break
        m = re.search(br"coding[:=]\s*([-\w.]+)", line)
        if m is not None:
            return m.group(1).decode("ascii")


if __name__ == "__main__":
    assert _encoding((b"; coding: big5\n", )) == "big5"
    assert _encoding((b"; coding: latin_1\n", )) == "latin_1"
    assert _encoding((b"; coding: latin-1\n", )) == "latin-1"
    assert _encoding((b"; test\n", b"; coding: big5\n")) == "big5"
    assert _encoding((b";", b"; test\n", b"; coding: big5\n")) is None
    assert _encoding((b"; coding: big5\n", )) == "big5"
    assert _encoding((b"; encoding: big5\n", )) == "big5"
    assert _encoding((b"# -*- coding: big5 -*-", )) == "big5"
    assert _encoding((b"# vim: set fileencoding=big5 :", )) == "big5"
    assert _encoding((b"\xef\xbb\xbf; coding: big5\n", )) == "utf-8"
