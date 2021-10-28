from hashlib import md5

from . import config, res

VERSION = "1.3.5"
IS_DEV_VERSION = config.debug_mode
CLIENT_COMPATIBILITY = "10"
SERVER_COMPATIBILITY = "0"


def server_is_compatible(version):
    if version in ["1.2-c12", "1.3.0", "1.3.1"]:
        version = "0"
    return version == SERVER_COMPATIBILITY


def compatibility_version():
    # Includes a hash of rules.txt.
    # (about the choice of MD5, check the comments in mapfile.py, line 45)
    # Don't check *.pyc (or library.zip, soundrts.exe and server.exe)
    # because it would require to add an internal version for every file.
    # (a bit complicated for the moment, and not as useful as checking rules.txt)
    return CLIENT_COMPATIBILITY + "-" + rules_hash()


def rules_hash():
    rules_and_ai = res.get_text_file("rules", append=True) + res.get_text_file(
        "ai", append=True
    )
    return md5(rules_and_ai.encode()).hexdigest()


# VERSION_FOR_BUG_REPORTS helps ignoring automatic bug reports related to
# modified code.
try:
    with open("lib/full_version.txt") as t:
        VERSION_FOR_BUG_REPORTS = t.read()
except OSError:
    VERSION_FOR_BUG_REPORTS = VERSION
