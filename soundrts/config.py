# read/write the config file

import ConfigParser
import platform
import re
import shutil

from lib.log import warning
from paths import CONFIG_FILE_PATH


login = "player"
num_channels = 16
speed = 1
srapi = 1
srapi_wait = .1
mods = ""
soundpacks = ""


def save():
    c = ConfigParser.SafeConfigParser()
    c.add_section("general")
    c.set("general", "login", login)
    c.set("general", "mods", mods)
    c.set("general", "soundpacks", soundpacks)
    c.set("general", "num_channels", repr(num_channels))
    c.set("general", "speed", repr(speed))
    c.add_section("tts")
    if platform.system() == "Windows":
        c.set("tts", "srapi", repr(srapi))
        c.set("tts", "srapi_wait", repr(srapi_wait))
    c.write(open(CONFIG_FILE_PATH, "w"))


def load():
    global login, num_channels, speed, mods, soundpacks
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
        error = True
    try:
        num_channels = c.getint("general", "num_channels")
    except:
        error = True
    try:
        speed = c.getint("general", "speed")
    except:
        error = True
    try:
        mods = c.get("general", "mods")
    except:
        error = True
    try:
        soundpacks = c.get("general", "soundpacks")
    except:
        error = True
    if platform.system() == "Windows":
        try:
            srapi_wait = c.getfloat("tts", "srapi_wait")
        except:
            error = True
        try:
            srapi = c.getint("tts", "srapi")
        except:
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


load()
