# read/write the config file

import configparser
import platform
import os
import re
import shutil
import sys

from .lib.log import info, warning
from .paths import CONFIG_FILE_PATH


def login_is_valid(login):
    return re.match("^[a-zA-Z0-9]{1,20}$", login) is not None

def login_type(s):
    assert isinstance(s, str)
    if not login_is_valid(s):
        raise ValueError
    return s

_options = [
    ("general", "login", "player", login_type),
    ("general", "mods", ""),
    ("general", "soundpacks", ""),
    ("general", "num_channels", 16),
    ("general", "speed", 1),
    ("general", "verbosity", "menu_changed,unit_added,unit_complete,scout_info,food,resources,resource_exhausted"),
    ("server", "timeout", 60.0),
    # fpct must be as small as possible while respecting test_fpct()
    ("server", "fpct_coef", 2.3),
    ("server", "fpct_max", 3),
    ("server", "require_humans", 0),
]

if platform.system() == "Windows":
    _options += [
        ("tts", "jaws", 0),
        ("tts", "srapi", 1),
        ("tts", "srapi_wait", .1),
    ]
else:
    _options += [
        ("tts", "jaws", 0),
        ("tts", "srapi", 0),
        ("tts", "srapi_wait", .1),
    ]

def add_converter(option):
    if len(option) == 4:
        return option
    return option + (type(option[2]), )

_options = [add_converter(o) for o in _options]

_module = sys.modules[__name__]

def save(name=CONFIG_FILE_PATH):
    c = configparser.ConfigParser()
    for section, option, _, _ in _options:
        if not c.has_section(section):
            c.add_section(section)
        c.set(section, option, str(getattr(_module, option)))
    c.write(open(name, "w"))

def make_a_copy(name):
    try:
        shutil.copy(name, name + ".old")
        warning("made a copy of the old config file")
    except:
        warning("could not make a copy of the old config file")

def _copy_to_module(c):
    error = False
    for section, option, default, converter in _options:
        try:
            raw_value = c.get(section, option)
        except configparser.Error:
            info("%r option is missing (will be: %r)", option, default)
            value = default
            error = True
        else:
            try:
                value = converter(raw_value)
            except ValueError:
                warning("%s will be %r instead of %r", option, default, raw_value)
                value = default
                error = True
        setattr(_module, option, value)
    return error

def load(name=CONFIG_FILE_PATH):
    if os.path.isfile(name):
        c = configparser.ConfigParser()
        c.read_file(open(name))
        error = _copy_to_module(c)
        if error:
            warning("Error in %s.", name)
            make_a_copy(name)
            warning("Rewriting %s...", name)
            save(name)
    else:
        init()
        save(name)

def init():
    for _, option, default, _ in _options:
        setattr(_module, option, default)

init()
