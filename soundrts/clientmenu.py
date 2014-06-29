import os
import re
import sys
import time

import pygame
from pygame.locals import *

from clienthelp import help_msg
from clientmedia import *
from commun import *
from paths import TMP_PATH


def string_to_msg(s):
    l = []
    for c in s:
        if c == ".":
            l.extend([5026])
        elif c in "0123456789":
            l.extend(nombre(c))
        else:
            l.extend(c)
    return l

def input_string(msg=[], pattern="^[a-zA-Z0-9]$", default=""):
    voice.menu(msg)
    s = default
    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        elif e.type == KEYDOWN:
            pygame.event.clear()
            if e.key in [K_LSHIFT, K_RSHIFT]:
                continue
            if e.key == K_RETURN:
                return s
            elif e.key == K_ESCAPE:
                return None
            elif e.key == K_BACKSPACE:
                s = s[:-1]
                voice.item(string_to_msg(s))
            elif re.match(pattern, e.unicode) != None:
                try:
                    c = e.unicode.encode("ascii") # telnetlib doesn't like unicode
                    s += c
                    voice.item(string_to_msg(c) + [9999] + string_to_msg(s))
                except:
                    warning("error reading character from keyboard")
                    voice.item([1003, 9999] + string_to_msg(s))
            else:
                voice.item([1003, 9999] + string_to_msg(s))
        elif e.type == USEREVENT:
            voice.update()
        voice.update() # XXX useful for SAPI

def _remember_path(menu_name):
    return os.path.join(TMP_PATH, menu_name + ".txt")

END_LOOP = 1


class Menu(object):

    server = None

    def __init__(self, title=None, choices=None, default_choice_index=0, remember=None):
        if not title:
            title = []
        self.title = title
        if not choices:
            choices = []
        self.choices = choices
        self.choice_index = None
        self.default_choice_index = default_choice_index
        self.remember = remember
        if self.remember is not None:
            try:
                self._remembered_choice = open(_remember_path(remember)).read()
            except:
                self._remembered_choice = ""

    def _say_choice(self):
        voice.item(self.choices[self.choice_index][0])

    def _choice_exists(self):
        return self.choice_index is not None and 0 <= self.choice_index < len(self.choices)

    def _select_previous_choice(self):
        if self.choices:
            if self.choice_index is None:
                self.choice_index = self.default_choice_index
            self.choice_index -= 1
            if not self._choice_exists():
                self.choice_index = len(self.choices) - 1
            self._say_choice()

    def _select_next_choice(self):
        if self.choices:
            if self.choice_index == None:
                self.choice_index = self.default_choice_index
            else:
                self.choice_index += 1
                if not self._choice_exists():
                    self.choice_index = 0
            self._say_choice()
            debug("select_next_choice %s", self.choice_index)
        else:
            debug("select_next_choice did nothing because choices=%s", self.choices)

    def _confirm_choice(self):
        if self._choice_exists() and self.choices[self.choice_index]:
            voice.confirmation(self.choices[self.choice_index][0][:1]) # repeat only the first part of the choice (not the help)
            self.choice_done = True
        else:
            debug("couldn't confirm choice (choices=%s, choice_index=%s)",
                  self.choices, self.choice_index)

    def _process_keydown(self, e):
        if e.key == K_TAB and e.mod & KMOD_ALT:
            return
        if e.key in [K_ESCAPE, K_LEFT]:
            self.choice_index = len(self.choices) - 1
            return self._confirm_choice()
        elif e.key == K_TAB and e.mod & KMOD_SHIFT or e.key == K_UP:
            self._select_previous_choice()
        elif e.key in [K_TAB, K_DOWN]:
            self._select_next_choice()
        elif e.key in [K_RETURN, K_RIGHT]:
            return self._confirm_choice()
        elif e.key == K_F1 and e.mod & KMOD_SHIFT or e.key == K_F2:
            voice.item(help_msg("menu", -1))
        elif e.key == K_F1:
            voice.item(help_msg("menu"))
        elif e.key == K_F5:
            voice.previous()
        elif e.key in [K_LALT,K_RALT]:
            voice.next()
        elif e.key == K_F6:
            voice.next(history_only=True)
        elif e.key in [K_HOME, K_KP_PLUS]:
            modify_volume(1)
        elif e.key in [K_END, K_KP_MINUS]:
            modify_volume(-1)
        elif e.unicode.lower() == "s":
            if self.server is None:
                voice.item([1029]) # hostile sound
            else:
                msg = input_string(msg=[4288], pattern="^[a-zA-Z0-9 ?!]$")
                if msg:
                    self.server.write_line("say %s" % msg)
        elif e.key not in [K_LSHIFT,K_RSHIFT]:
            voice.item([4052])

    def append(self, label, action):
        self.choices.append((label, action))
        if self.remember is not None and self._remembered_choice == repr(label):
            self.default_choice_index = len(self.choices) - 1

    def update_menu(self, menu):
        debug("update_menu...")
        old_title = self.title
        old_choices = self.choices
        try:
            old_choice = self.choices[self.choice_index]
        except (IndexError, TypeError):
            old_choice = None
        self.title, self.choices = menu.title, menu.choices
        if self.title and self.title != old_title:
            debug("...new title")
            voice.menu(self.title)
        if self.choices != old_choices:
            debug("...new choices")
            self.choice_index = None
            if old_choice in self.choices:
                self.choice_index = self.choices.index(old_choice)

    def _execute_choice(self):
        label, action = self.choices[self.choice_index]
        if hasattr(action, "run"):
            if action.run() == END_LOOP:
                self.end_loop = True
        elif callable(action):
            if action() == END_LOOP:
                self.end_loop = True
        elif isinstance(action, tuple) and len(action) > 1 and callable(action[0]):
            if action[0](*action[1:]) == END_LOOP:
                self.end_loop = True
        elif action == END_LOOP:
            self.end_loop = True
        if self.remember is not None and action is not None:
            open(_remember_path(self.remember), "w").write(repr(label))
            # default_choice_index might be useful soon
            # for example: ServerMenu._get_creation_submenu()
            self.default_choice_index = self.choice_index
        else:
            self.default_choice_index = 0
        self.choice_index = None

    def _try_to_get_choice(self, e):
        if e.type == QUIT:
            sys.exit()
        if e.type == USEREVENT:
            voice.update()
        elif e.type == KEYDOWN:
            self._process_keydown(e)
        voice.update() # XXX useful for SAPI

    def _get_choice_from_static_menu(self):
        self.choice_done = False
        while not self.choice_done:
            self._try_to_get_choice(pygame.event.poll())
            time.sleep(.01)

    def step(self):
        self.choice_done = False
        self._try_to_get_choice(pygame.event.poll())
        if self.choice_done:
            self._execute_choice()
    
    def run(self):
        if self.title:
            voice.menu(self.title)
        else:
            voice.menu([4007])
        self._get_choice_from_static_menu()
        self._execute_choice()

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self.run()
