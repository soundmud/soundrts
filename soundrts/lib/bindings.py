import re

import pygame
from pygame import KMOD_CTRL, KMOD_ALT, KMOD_SHIFT
from pygame import K_LCTRL, K_LALT, K_LSHIFT, K_RCTRL, K_RALT, K_RSHIFT

from .log import warning


class _Error(Exception):
    pass


_allowed_mods = ("CTRL", "ALT", "SHIFT")

def _normalized_key(s):
    words = s.split()
    mods = words[:-1]
    for mod in mods:
        if mod not in _allowed_mods:
            raise _Error("'%s' is not an allowed key modifier" % mod)
    normalized_mods = tuple(1 if m in mods else 0 for m in _allowed_mods)
    try:
        key = getattr(pygame, "K_" + words[-1])
    except AttributeError:
        raise _Error("'%s' is not a key" % words[-1])
    return normalized_mods, key

_mod_masks = (KMOD_CTRL, KMOD_ALT, KMOD_SHIFT)
_modifiers_as_keys = (K_LCTRL, K_LALT, K_LSHIFT, K_RCTRL, K_RALT, K_RSHIFT)

def _normalized_event(e):
    if e.key in _modifiers_as_keys:
        # modifiers never modify another modifier
        normalized_mods = (0, 0, 0)
    else:
        normalized_mods = tuple(1 if e.mod & m else 0 for m in _mod_masks)
    return normalized_mods, e.key

def _preprocess(s):
    s = re.sub("(?m);.*$", "", s) # remove comments
    s = re.sub("(?m)^[ \t]*$\n", "", s) # remove empty lines
    s = re.sub(r"(?m)\\[ \t]*$\n", " ", s) # join lines ending with "\"
    return s


class Bindings:

    def __init__(self):
        self._bindings = {}
        self._definitions = dict()

    def _apply_definitions(self, line):
        # "\w" means "alphanumeric character (or the underscore)"
        # "(?<!\w)" means "no '\w' before"
        # "(?!\w)" means "no '\w' after"
        for name, value in list(self._definitions.items()):
            # replace name with value
            line = re.sub(r"(?<!\w)%s(?!\w)" % name, value, line)
        return line

    def _add_definition(self, line):
        try:
            _, name, value = line.strip().split(" ", 2)
        except ValueError:
            raise _Error("the defined value is missing")
        self._definitions[name] = value

    def _add_binding(self, line, command_from_name):
        key_string, command_string = line.strip().split(":", 1)
        normalized_key = _normalized_key(key_string)
        try:
            command_name, args = command_string.split(None, 1)
        except ValueError:
            command_name = command_string.strip()
            args = ""
        # Note: maybe the client should interpret the args string
        # and eventually provide a preformatter and a validator
        # for each command. For example to avoid splitting then joining again.
        command = command_from_name(command_name), args.split()
        self._bindings[normalized_key] = command

    def _process_line(self, line, command_from_name):
        if line.startswith("#define "):
            self._add_definition(line)
        elif ":" in line:
            self._add_binding(line, command_from_name)
        elif line:
            raise _Error("the line must be a binding or a definition")

    def load(self, s, client, prefix="cmd"):
        def command_from_name(name):
            try:
                return getattr(client, prefix + "_" + name)
            except AttributeError:
                raise _Error("'%s' is not a command" % name)
        for line in _preprocess(s).split("\n"):
            try:
                line = self._apply_definitions(line)
                self._process_line(line, command_from_name)
            except _Error as err:
                warning("error in bindings.txt (line ignored):\n%s\n(%s)", line, err)

    def process_keydown_event(self, e):
        # will raise KeyError if no binding exists for this event
        cmd, args = self._bindings[_normalized_event(e)]
        cmd(*args)
