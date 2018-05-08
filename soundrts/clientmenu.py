import os
import re
import sys
import time

import pygame
from pygame.locals import QUIT, KEYDOWN, K_LSHIFT, K_RSHIFT, K_KP_ENTER, K_RETURN, K_ESCAPE, K_BACKSPACE, USEREVENT, K_TAB, KMOD_ALT, K_LEFT, K_UP, KMOD_SHIFT, K_DOWN, K_RIGHT, K_F2, KMOD_CTRL, K_F1, K_F5, K_LALT, K_RALT, K_F6, K_HOME, K_KP_PLUS, K_END, K_KP_MINUS, K_F7

from clienthelp import help_msg
from clientmedia import voice, modify_volume, toggle_fullscreen, sounds
from lib.log import warning
from lib.msgs import nb2msg
from lib.sound import psounds
import msgparts as mp
from paths import TMP_PATH


CONFIRM_SOUND = 6116
SELECT_SOUND = 6115


def string_to_msg(s, spell=True):
    if not spell:
        return [s]
    l = []
    for c in s:
        if c == ".":
            l.extend(mp.DOT)
        elif c in "0123456789":
            l.extend(nb2msg(c))
        else:
            l.extend(c)
    return l

def input_string(msg=[], pattern="^[a-zA-Z0-9]$", default="", spell=True):
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
            if e.key in (K_RETURN, K_KP_ENTER):
                voice.item([s])
                return s
            elif e.key == K_ESCAPE:
                return None
            elif e.key == K_BACKSPACE:
                s = s[:-1]
                voice.item(string_to_msg(s, spell))
            elif re.match(pattern, e.unicode) != None:
                try:
                    c = e.unicode.encode("ascii") # telnetlib doesn't like unicode
                    s += c
                    voice.item(string_to_msg(c)
                               + mp.PERIOD
                               + string_to_msg(s, spell))
                except:
                    warning("error reading character from keyboard")
                    voice.item(mp.BEEP + mp.PERIOD + string_to_msg(s, spell))
            else:
                voice.item(mp.BEEP + mp.PERIOD + string_to_msg(s, spell))
        elif e.type == USEREVENT:
            voice.update()
        voice.update() # useful for SAPI

def _remember_path(menu_name):
    return os.path.join(TMP_PATH, menu_name + ".txt")

CLOSE_MENU = 1


def _first_letter(choice):
    if choice:
        for sound_number in choice[0]:
            try:
                return sounds.translate_sound_number(sound_number)[0].lower()
            except:
                pass


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
        psounds.play_stereo(sounds.get_sound(SELECT_SOUND))
        choice = self.choices[self.choice_index]
        msg = list(choice[0])
        if len(choice) > 2:
            msg +=  mp.COMMA + choice[2]
        voice.item(msg)

    def _choice_exists(self):
        return self.choice_index is not None and 0 <= self.choice_index < len(self.choices)

    def _select_next_choice(self, first_letter=None, inc=1):
        if self.choices:
            if self.choice_index is None:
                self.choice_index = self.default_choice_index
                if inc == -1:
                    self.choice_index -= 1
            else:
                self.choice_index += inc
                self.choice_index %= len(self.choices)
            if first_letter:
                found = False
                for _ in range(len(self.choices)):
                    choice = self.choices[self.choice_index]
                    if _first_letter(choice) == first_letter.lower():
                        found = True
                        break
                    self.choice_index += inc
                    self.choice_index %= len(self.choices)
                if not found:
                    self.choice_index -= inc
                    self.choice_index %= len(self.choices)
                    return 
            self._say_choice()

    def _confirm_choice(self):
        psounds.play_stereo(sounds.get_sound(CONFIRM_SOUND))
        if self._choice_exists() and self.choices[self.choice_index]:
            voice.confirmation(self.choices[self.choice_index][0])
            self.choice_done = True

    def _process_keydown(self, e):
        if e.key in [K_ESCAPE, K_LEFT]:
            self.choice_index = len(self.choices) - 1
            return self._confirm_choice()
        elif e.key == K_TAB and e.mod & KMOD_SHIFT or e.key == K_UP:
            self._select_next_choice(inc=-1)
        elif e.key in [K_TAB, K_DOWN]:
            self._select_next_choice()
        elif e.key in (K_RETURN, K_KP_ENTER, K_RIGHT):
            return self._confirm_choice()
        elif e.key == K_F2 and e.mod & KMOD_CTRL:
            toggle_fullscreen()
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
        elif e.key == K_F7:
            if self.server is None:
                voice.item(mp.BEEP)
            else:
                msg = input_string(msg=mp.ENTER_MESSAGE,
                                   pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+=?!]$",
                                   spell=False)
                if msg:
                    self.server.write_line("say %s" % msg)
        elif e.unicode and e.mod & KMOD_SHIFT:
            self._select_next_choice(e.unicode, -1)
        elif e.unicode:
            self._select_next_choice(e.unicode)
        elif e.key not in [K_LSHIFT,K_RSHIFT]:
            voice.item(mp.SELECT_AND_CONFIRM_EXPLANATION)

    def append(self, label, action, explanation=None):
        if explanation is None:
            explanation = []
        self.choices.append((label, action, explanation))
        if self.remember is not None and self._remembered_choice == repr(label):
            self.choices.insert(0, (label, action))

    def update_menu(self, menu):
        old_title = self.title
        old_choices = self.choices
        try:
            old_choice = self.choices[self.choice_index]
        except (IndexError, TypeError):
            old_choice = None
        self.title, self.choices = menu.title, menu.choices
        if self.title and self.title != old_title:
            voice.menu(self.title)
        if self.choices != old_choices:
            self.choice_index = None
            if old_choice in self.choices:
                self.choice_index = self.choices.index(old_choice)

    def _execute_choice(self):
        label, action = self.choices[self.choice_index][:2]
        def cmd(): pass
        args = ()
        if hasattr(action, "run"):
            cmd = action.run
        elif callable(action):
            cmd = action
        elif isinstance(action, tuple):
            cmd = action[0]
            args = action[1:]
        elif action == CLOSE_MENU:
            def cmd(): return CLOSE_MENU
        if cmd(*args) == CLOSE_MENU:
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
        voice.update() # useful for SAPI

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
            voice.menu(mp.MAKE_A_SELECTION2)
        self._get_choice_from_static_menu()
        self._execute_choice()

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self.run()
