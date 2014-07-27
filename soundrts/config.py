# read/write the config file

import ConfigParser
import optparse
import platform
import re
import shutil

from lib.log import *

from paths import *


def save():
    c = ConfigParser.SafeConfigParser()
    c.add_section("general")
    c.set("general", "login", login)
    c.set("general", "mods", _mods)
    c.set("general", "num_channels", repr(num_channels))
    c.set("general", "speed", repr(speed))
    c.add_section("tts")
    if platform.system() == "Windows":
        c.set("tts", "srapi", repr(srapi))
        c.set("tts", "srapi_wait", repr(srapi_wait))
    c.write(open(CONFIG_FILE_PATH, "w"))

def load():
    global login, num_channels, speed, _mods
    global srapi, srapi_wait
    error = False
    new_file = False
    try:
        f = open(CONFIG_FILE_PATH)
    except:
        new_file = True
    try:
        c = ConfigParser.SafeConfigParser()
        c.readfp(f)
    except:
        error = True
    try:
        login = c.get("general", "login")
        if re.match("^[a-zA-Z0-9]{1,20}$", login) == None:
            raise ValueError
    except:
        login = "player"
        error = True
    try:
        num_channels = c.getint("general", "num_channels")
    except:
        num_channels = 16
        error = True
    try:
        speed = c.getint("general", "speed")
    except:
        speed = 1
        error = True
    try:
        _mods = c.get("general", "mods")
    except:
        _mods = ""
        error = True
    if platform.system() == "Windows":
        try:
            srapi_wait = c.getfloat("tts", "srapi_wait")
        except:
            srapi_wait = .1
            error = True
        try:
            srapi = c.getint("tts", "srapi")
        except:
            srapi = 1
            error = True
    if error and not new_file:
        warning("rewriting SoundRTS.ini...")
        try:
            n_old = CONFIG_FILE_PATH + ".old"
            shutil.copy(CONFIG_FILE_PATH, n_old)
            warning("made a copy of old config file")
        except:
            warning("could not make a copy of old config file")
    save()

def _parse_options():
    global options, port, record_games
    default_port = 2500
    parser = optparse.OptionParser()
    parser.add_option("-m", "--mods", type="string")
    parser.add_option("-p", type="int", help=optparse.SUPPRESS_HELP)
    parser.add_option("-g", action="store_true", help=optparse.SUPPRESS_HELP)
    parser.set_defaults(mods=None, p=default_port, g=False)
    options, _ = parser.parse_args()
    port = options.p
    record_games = options.g
    if port != default_port:
        warning("using port %s (instead of %s)", port, default_port)
    if record_games:
        warning("games will be recorded on the server")

_parse_options()
load()
# If config.save() is called (for example when the player's name is recorded),
# the "--mods=" command-line option must not be saved in SoundRTS.ini .
# That's why the "mods =" parameter from SoundRTS.ini is kept in a separate
# variable.
if options.mods is not None:
    mods = options.mods
else:
    mods = _mods
mixer_freq = 44100 # 22050 # 16000 # 11025
