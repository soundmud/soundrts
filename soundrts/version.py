from __future__ import absolute_import
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import os

from . import res


VERSION = "1.3-b1-dev"
IS_DEV_VERSION = VERSION.endswith("-dev")


def _remove_dev(s):
    if s.endswith("-dev"):
        return s[:-4]
    else:
        return s


def compatibility_version():
# Includes a hash of rules.txt.
# (about the choice of MD5, check the comments in mapfile.py, line 45)
# Don't check *.pyc (or library.zip, soundrts.exe and server.exe)
# because it would require to add an internal version for every file.
# (a bit complicated for the moment, and not as useful as checking rules.txt)
# TODO: use Git to include a version in every *.pyc? (check other projects)
    return _remove_dev(VERSION) + "-" + rules_hash()


def rules_hash():
    rules_and_ai = res.get_text_file("rules", append=True) + res.get_text_file("ai", append=True)
    return md5(rules_and_ai.encode()).hexdigest()


# VERSION_FOR_BUG_REPORTS helps ignoring automatic bug reports related to
# modified code.
try:
    _s = os.path.getsize("library.zip")
except os.error:
    _s = 0
VERSION_FOR_BUG_REPORTS = "%s (%s)" % (VERSION, _s)
