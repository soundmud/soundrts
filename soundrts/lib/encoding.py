# similar to http://www.python.org/dev/peps/pep-0263/
import codecs
import locale
import re

from soundrts.lib.log import warning


def _get_encoding_from_first_or_second_line(text, filename):
    for line in text.split(b"\n")[:2]:
        m = re.search(br"coding[:=]\s*([-\w.]+)", line)
        if m is not None:
            e = m.group(1).decode("ascii")
            try:
                return codecs.lookup(e).name
            except LookupError:
                warning(f"unknown encoding in {filename}: {e}")


def encoding(text, filename="test.txt"):
    e = _get_encoding_from_first_or_second_line(text, filename)
    if text.startswith(b"\xef\xbb\xbf"):  # UTF-8 with BOM signature
        if e and e.lower() not in ["utf8", "utf-8", "utf_8"]:
            warning(f"{filename} starts with an UTF-8 BOM signature but specifies a {e} encoding! using utf-8-sig")
        return "utf-8-sig"  # the signature will be skipped
    if e is None:
        try:
            import chardet
            e = chardet.detect(text)["encoding"]
        except ImportError:
            e = locale.getpreferredencoding()
        warning(f"no encoding specified for {filename}, using {e}")
    return e


if __name__ == "__main__":
    GUESS_OR_DEFAULT = ["ascii", locale.getpreferredencoding()]
    assert encoding(b"; coding: big5\n") == "big5"
    assert encoding(b"; coding: big-5\n") in GUESS_OR_DEFAULT  # unknown encoding
    assert encoding(b"; coding: latin_1\n") == "iso8859-1"
    assert encoding(b"; coding: latin-1\n") == "iso8859-1"
    assert encoding(b"; test\n; coding: big5\n") == "big5"
    assert encoding(b";\n; test\n; coding: big5\n") in GUESS_OR_DEFAULT  # specified on third line
    assert encoding(b"; coding: big5\n") == "big5"
    assert encoding(b"; encoding: big5\n") == "big5"
    assert encoding(b"# -*- coding: big5 -*-") == "big5"
    assert encoding(b"# vim: set fileencoding=big5 :") == "big5"
    assert encoding(b"\xef\xbb\xbf; coding: big5\n") == "utf-8-sig"
    assert b"\xef\xbb\xbf; coding: big5\n".decode("utf-8-sig") == "; coding: big5\n"
