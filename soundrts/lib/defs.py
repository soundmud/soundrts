import re


def _remove_comments(s):
    r"""
    >>> _remove_comments(";aaa")
    ''
    >>> _remove_comments("eeeee;aaa\nzzzzz")
    'eeeee\nzzzzz'
    """
    return re.sub("(?m);.*$", "", s)

def _remove_empty_lines(s):
    return re.sub("(?m)^[ \t]*$\n", "", s)

def _join_lines(s):
    r"""Joins lines ending with an antislash.

    The antislash is replaced with a space.
    >>> _join_lines("a\\\na")
    'a a'

    Trailing spaces are ignored.
    >>> _join_lines("a\\   \na")
    'a a'
    """
    return re.sub(r"(?m)\\[ \t]*$\n", " ", s)

def preprocess(s):
    r"""
    A comment line doesn't count if between two joined lines.
    >>> preprocess("on\\\n; comment\nthe same line")
    'on the same line'
    """
    s = _remove_comments(s)
    s = _remove_empty_lines(s)
    s = _join_lines(s)
    return s


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    if "idlelib" not in dir():
        input("press ENTER to exit")
