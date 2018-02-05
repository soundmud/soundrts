import math
import Queue
import re
import sys
import time

import pygame
from pygame.locals import KEYDOWN, QUIT, USEREVENT, K_TAB, KMOD_ALT, MOUSEBUTTONDOWN, KMOD_SHIFT, KMOD_CTRL, MOUSEBUTTONUP, MOUSEMOTION

from clientgamegridview import GridView
from clientgamefocus import Zoom
from clienthelp import help_msg
from clientmedia import voice, sounds, sound_stop, modify_volume, get_fullscreen, toggle_fullscreen, play_sequence
from lib.mouse import set_cursor
from clientmenu import Menu, string_to_msg
from clientgameentity import EntityView
from clientgamenews import must_be_said
from clientgameorder import order_title, order_shortcut, order_args, order_comment, order_index
import config
from constants import ALERT_LIMIT, EVENT_LIMIT, VIRTUAL_TIME_INTERVAL
from definitions import style
from lib import group
from lib.log import debug, warning, exception
from lib.msgs import nb2msg, eval_msg_and_volume
from lib.nofloat import PRECISION
from version import VERSION
from lib.sound import psounds, distance, angle, vision_stereo, stereo
from lib.screen import set_game_mode, screen_render, get_screen,\
    screen_render_subtitle


POSITIONAL_SOUND = ["1003"]  # TODO: include this in style.txt


def direction_to_msgpart(o):
    o = round(o / 45.0) * 45.0
    while o >= 360:
        o -= 360
    while o < 0:
        o += 360
    if o == 0:
        s = 69 # E
    elif o == 45:
        s = 71 # NE
    elif o == 90:
        s = 67 # N
    elif o == 135:
        s = 72 # NW
    elif o == 180:
        s = 70 # W
    elif o == 225:
        s = 74 # SW
    elif o == 270:
        s = 68 # S
    elif o == 315:
        s = 73 # SE
    return s


class GameInterface(object):

    last_virtual_time = 0
    x = y = o = 0
    place = None
    mouse_select_origin = None
    collision_debug = None
    shortcut_mode = False
    zoom_mode = False
    zoom = None

    def __init__(self, server, speed=config.speed):
        self.server = server
        self.speed = speed
        self.alert_squares = {}
        self.dobjets = {}
        self.group = []
        self.groups = {}
        self.lost_units = []
        self.neutralized_units = []
        self.previous_menus = {}
        self.scout_info = set()
        server.interface = self
        self.grid_view = GridView(self)
        self.set_self_as_listener()
        self._reset_typing()
        voice.silent_flush()
        self._srv_queue = Queue.Queue()
        self.scouted_squares = ()
        self.scouted_before_squares = ()

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict["_srv_queue"]
        return odict

    def __setstate__(self, dictionary):
        self.__dict__.update(dictionary)
        self._srv_queue = Queue.Queue()

    def set_self_as_listener(self):
        psounds.set_listener(self)

    @property
    def player(self):
        try:
            return self.server.player
        except:
            return None

    _square_width = None
    
    @property
    def square_width(self):
        if self._square_width is None:
            self._square_width = self.server.player.world.square_width / 1000.0
        return self._square_width

    def _process_srv_event(self, *e):
        cmd = "srv_" + e[0]
        if hasattr(self, cmd):
            getattr(self, cmd)(*e[1:])
        else:
            warning("Not recognized: %s" % e[0])

    def srv_event(self, o, e):
        try:
            if hasattr(self, "next_update") and \
               time.time() > self.next_update + EVENT_LIMIT:
                return
            EntityView(self, o).notify(e)
        except:
            exception("problem during srv_event")

    def _type(self, kind, msg=[], pattern="^[a-zA-Z0-9]$", spell=True):
        voice.item(msg)
        self.typing_mode = True
        self.typing_buffer = ""
        self.typing_kind = kind
        self.typing_pattern = pattern
        self.typing_spell = spell

    def cmd_say(self):
        self._type("chat", msg=[4288], pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+=?!]$", spell=False)

    def _finished_typing_chat(self, msg):
        self._reset_typing()
        if not msg:
            return
        voice.confirmation([self.player.client.login, 4287, msg])
        self.server.write_line("say %s" % msg)

    def cmd_say_players(self):
        l = []
        for p in self.server.player.world.players:
            if p.number is not None:
                l.append([p.number, p.name])
        l.sort()
        for n, name in l:
            voice.info(nb2msg(n) + [9998, name, 9999])

    def srv_msg(self, s):
        voice.info(*eval_msg_and_volume(s))

    def srv_voice_important(self, s):
        voice.confirmation(*eval_msg_and_volume(s)) # remember the pressed key
#        voice.important(*eval_msg_and_volume(s))

    def srv_speed(self, s):
        self.speed = float(s)

    def srv_sequence(self, parts):
        play_sequence(parts)

    def srv_quit(self):
        voice.silent_flush()
        sound_stop()
        self.end_loop = True

    def distance(self, o):
        return distance(self.x, self.y, o.x, o.y)

    # select target

    target = None

    def _priority(self, o):
        p = 10
        if self.an_order_requiring_a_target_is_selected:
            if self.order.startswith("build") and o.is_a_building_land:
                p = 0
        else:
            if o.qty > 0:
                p = 1 + o.resource_type / 100.0 # less than 100 resource types
            elif o.is_repairable and o.hp < o.hp_max:
                p = 2
            elif o.is_a_building_land:
                p = 3
            elif hasattr(o, "other_side"):
                p = 4
        return [p, len(o.title), self.distance(o)]

    def is_visible(self, o):
        if self.zoom_mode and not self.zoom.contains(o):
            return False
        if not o.is_in(self.place) or not o.title:
            return False
        if self.immersion:
            if o.id in self.group:
                return False
            else:
                # visible if in front of you (190 degrees field)
                a = angle(self.x, self.y, o.x, o.y, self.o)
                return math.cos(a) > math.cos(math.radians(95))
        else:
            return True

    def is_selectable(self, o):
        # must be in the current square or in front of the observer
        return self.is_visible(o)
        # XXX == is_known ? (is_remembered or seen)

    def _object_choices(self, inc, types):
        choices = []
        for o in self.dobjets.values():
            if self.is_selectable(o) and (
                not types or getattr(o, "type_name", None) in types
                or "useful" in types and o.is_a_useful_target()):
                choices.append(o)
        choices.sort(key=self._priority)
        if inc == -1:
            choices.reverse()
        return choices

    def say_target(self):
        if self.an_order_requiring_a_target_is_selected:
            d, vg, vd = self.get_description_of(self.target)
            voice.item(d + order_title(self.order), vg, vd)
        else:
            voice.item(*self.get_description_of(self.target))

    def get_description_of(self, o):
        if self.immersion:
            vg, vd = vision_stereo(self.x, self.y, o.x, o.y, self.o)
            return POSITIONAL_SOUND + o.title + [54] + nb2msg(self.distance(o)) + [55] \
                   + self.direction_to_msg(o) + o.description, vg, vd
        else:
            self.o = 90
            vg, vd = vision_stereo(self.x, self.y, o.x, o.y, self.o)
            return POSITIONAL_SOUND + o.title + self.direction_to_msg(o) + o.description, vg, vd

    def cmd_examine(self):
        if self.target is not None:
            self.say_target()
        elif self.zoom_mode:
            self.zoom.say()
        else:
            self.say_square(self.place)

    def _next_choice(self, choice, choices):
        sel = 0
        try:
            sel = choices.index(choice) + 1
        except ValueError:
            pass
        if sel >= len(choices):
            sel = 0
        return choices[sel]

    def cmd_select_target(self, inc, *types):
        inc = int(inc)
        choices = self._object_choices(inc, types)
        if choices:
            self.target = self._next_choice(self.target, choices)
            self.say_target()
        else:
            voice.item([0]) # "nothing"
            self.target = None

    # misc

    def cmd_objectives(self):
        msg = []
        if self.player.world.introduction:
            msg += self.player.world.introduction + [9999]
        if self.player.objectives:
            msg += [4020, 9998] # "objectives:"
            for o in self.player.objectives.values():
                msg += o.description + [9998]
        voice.item(msg)

    def cmd_toggle_cheatmode(self):
        if self.server.allow_cheatmode:
            self.server.write_line("toggle_cheatmode")
            if self.server.player.cheatmode:
                voice.item([4265, 4264]) # is now off
            else:
                voice.item([4265, 4263]) # is now on
        else:
            voice.item([1029]) # hostile sound

    def cmd_console(self):
        if self.server.allow_cheatmode:
            self._type("cmd", msg=[4317], pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+=?!]$", spell=False)
        else:
            voice.item([1029]) # hostile sound

    def _finished_typing_cmd(self, cmd):
        self._reset_typing()
        if cmd is None:
            return
        if cmd.startswith("s "):
            self.speed = float(cmd.split(" ")[1])
            self.next_update = time.time()
        elif cmd == "p":
            if self.speed >= 1:
                self.speed /= 10000.0
            else:
                self.speed *= 10000.0
                self.next_update = time.time()
        elif cmd == "m":
            for u in self.player.units:
                u.mana_regen *= 1000
        elif cmd == "h":
            voice.item(["p: pause/unpause, s: set speed, r: get 1000 resources, t: get all techs, m: infinite mana, a: add units, v: instant victory"])
        elif cmd == "r":
            self.player.resources = [n + 1000 * PRECISION for n in self.player.resources]
        elif cmd == "t":
            self.player.has = lambda x: True
        elif cmd:
            # This direct way of executing the command might be a bit buggy,
            # but at the moment this feature is just for cheating or testing anyway.
            cmd = re.sub("^a ", "add_units %s " % getattr(self.place, "name", ""), cmd)
            cmd = re.sub("^v$", "victory", cmd)
            try:
                self.player.my_eval(cmd.split())
            except:
                voice.item([1029]) # hostile sound

    def cmd_change_player(self):
        if self.server.allow_cheatmode:
            self.server.write_line("change_player")
            voice.item([60] + [self.player.name]) # "You are..."
        else:
            voice.item([1029]) # hostile sound
        
    def cmd_volume(self, inc=1):
        modify_volume(int(inc))

    def cmd_history_previous(self):
        voice.previous()

    def cmd_history_stop(self):
        voice.next()

    def cmd_history_next(self):
        voice.next(history_only=True)

    def cmd_gamemenu(self):
        voice.silent_flush()
        sound_stop()
        menu = Menu([4010], [
            ([4070], self.gm_quit),
            ([4103], self.gm_slow_speed),
            ([4104], self.gm_normal_speed),
            ([4105], self.gm_fast_speed),
            ([4105] + nb2msg(4), self.gm_very_fast_speed),
            ])
        if self.can_save():
            menu.append([4112], self.gm_save)
##            menu.append([4113], self.gm_restore)
        menu.append([4071], None)
        set_game_mode(False)
        menu.run()
        set_game_mode(True)

    already_asked_to_quit = False
    forced_quit = False

    def gm_quit(self):
        if not self.already_asked_to_quit:
            self.server.write_line("quit")
            pygame.event.clear()
            self.already_asked_to_quit = True
        else:
            self.srv_quit() # forced quit
            self.forced_quit = True

    def _set_speed(self, speed):
        self.server.write_line("speed %s" % speed)
        self.speed = speed # XXX too early? if not allowed?

    def gm_slow_speed(self):
        self._set_speed(.5)

    def gm_normal_speed(self):
        self._set_speed(1.0)

    def gm_fast_speed(self):
        self._set_speed(2.0)

    def gm_very_fast_speed(self):
        self._set_speed(4.0)

    def can_save(self):
        return hasattr(self.server, "save_game")

    def gm_save(self):
            self.server.save_game()


    # clock

    talking_clock_enabled = False
    last_nb_minutes = 0

    def cmd_toggle_talking_clock(self):
        self.talking_clock_enabled = not self.talking_clock_enabled
        if self.talking_clock_enabled:
            voice.item([1039, 1003, 4263]) # is now on
            self.last_nb_minutes = int(self.last_virtual_time / 60)
        else:
            voice.item([1039, 1003, 4264]) # is now off

    def talking_clock(self): # bell, in fact
        if self.talking_clock_enabled:
            nb_minutes = int(self.last_virtual_time / 60)
            if self.last_nb_minutes != nb_minutes:
                voice.important([1003]) # + nb2msg(nb_minutes) + [65])
                self.last_nb_minutes = nb_minutes

    def cmd_say_time(self):
        m, s = divmod(int(self.last_virtual_time), 60)
        voice.item(nb2msg(m) + [65] + nb2msg(s) + [66])

    _must_play_tick = False

    _average_game_turn_time = 0
    _previous_play_tick_time = None

    def _play_tick(self):
        if self._must_play_tick:
            psounds.play_stereo(sounds.get_sound(1003), vol=.1)
        # record game turn time
#        nb_samples = 3.0
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / self.speed
        nb_samples = max(1.0, 1.0 / interval)
#        nb_samples = max(1.0, self._average_game_turn_time)
        if self._previous_play_tick_time is None:
            self._previous_play_tick_time = time.time()
        self._average_game_turn_time = (self._average_game_turn_time * (nb_samples - 1) + time.time() - self._previous_play_tick_time) / nb_samples
        self._previous_play_tick_time = time.time()

    def display_tps(self):
        if self._must_play_tick and self._average_game_turn_time != 0:
            tps = 1 / self._average_game_turn_time
            basic_tps = 1 / (VIRTUAL_TIME_INTERVAL / 1000.0)
            relative = tps / basic_tps
            screen_render("tps=%.0f" % tps, (0, 0))
            screen_render("%.1f" % relative, (0, 15))

    def cmd_toggle_tick(self):
        self._must_play_tick = not self._must_play_tick

    # loop

    def srv_voila(self, t, memory, perception, scouted_squares, scouted_before_squares, collision_debug):
        self.last_virtual_time = float(t) / 1000.0
        if not self.asked_to_update:
            self._ask_for_update()
        self.asked_to_update = False

        self.memory = memory
        self.perception = perception
        self.scouted_squares = scouted_squares
        self.scouted_before_squares = scouted_before_squares
        self.collision_debug = collision_debug

        self.talking_clock()
        self.send_resource_alerts_if_needed()
        if self.previous_menus == {}:
            self.send_menu_alerts_if_needed() # init
        self.units_alert_if_needed()
        self.squares_alert_if_needed()
        self.scout_info_if_needed()

        self.update_fog_of_war()
        self.update_group()
        self.display()

    asked_to_update = False

    def _ask_for_update(self):
        self._play_tick()
        self.asked_to_update = True
        self.server.write_line("update")
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / self.speed
        self.next_update = max(time.time(), self.next_update + interval)

    def _ask_for_update_if_needed(self):
        # ask server: "what's new?" (the clients activate the server update)
        if not self.asked_to_update and time.time() >= self.next_update:
            if len(self.server.data) != 0:
                debug("It's time to send cmd_update... "
                      "and all data is not received!")
                debug("The data is:\n%s", self.server.data)
            self._ask_for_update()

    def _remind_server_if_needed(self):
        if self.asked_to_update and time.time() >= self.next_update:
            self.server.write_line("no_end_of_update_yet")

    previous_animation = 0

    def _animate_objects(self):
        if time.time() >= self.previous_animation + .1:
            self.set_obs_pos()
            for o in self.dobjets.values():
                o.animate()
            self.previous_animation = time.time()

    def _process_events(self):
        # Warning: only sound/voice/keyboard events here, no server event.
        # Because a bad loop might occur when called from a function
        # waiting for a combat sound to end.
        for e in pygame.event.get():
            if e.type == USEREVENT:
                voice.update()
                continue
            if e.type == USEREVENT + 1:
                psounds.update()
                continue
            try:
                if e.type == QUIT:
                    sys.exit()
                elif e.type == KEYDOWN:
                    if e.key == K_TAB and e.mod & KMOD_ALT:
                        return # continue ?
                    if self.shortcut_mode:
                        self._execute_order_shortcut(e)
                        continue
                    elif self.typing_mode:
                        self._execute_typing(e)
                        continue
                    for binding in self.bindings:
                        if self._launch_binding_if_event(e, *binding):
                            break
#                    self.execute_keydown_event(e)
                    self.display()
                elif get_fullscreen():
                    if e.type == MOUSEMOTION:
                        square = self.grid_view.square_from_mousepos(e.pos)
                        target = self.grid_view.object_from_mousepos(e.pos)
                        if target is not None:
                            if target != self.target:
                                self.target = target
                                self.say_target()
                                self.display()
                                if self.an_order_requiring_a_target_is_selected:
                                    if self.order.find("build") == 0:
                                        set_cursor("square")
                                    else:
                                        set_cursor("target")
                                else:
                                    set_cursor("diamond")
                        elif square is not None:
                            if square != self.place or self.target is not None:
                                self._select_and_say_square(square)
                                self.target = target
                                if self.an_order_requiring_a_target_is_selected:
                                    if self.order.find("build") == 0:
                                        set_cursor("square")
                                    else:
                                        set_cursor("target")
                                else:
                                    set_cursor("tri_left")
                    elif e.type == MOUSEBUTTONDOWN:
                        if e.button == 1: # left mouse button
                            if self.an_order_requiring_a_target_is_selected:
                                mods = pygame.key.get_mods()
                                args = []
                                if mods & KMOD_SHIFT:
                                    args += ["queue_order"]
                                if mods & KMOD_CTRL:
                                    args += ["imperative"]
                                self.cmd_validate(*args)
                            else:
                                self.mouse_select_origin = e.pos
                        elif e.button == 3: # right mouse button
                            # do nothing if the mouse is pointing on nothing
                            if self.grid_view.square_from_mousepos(e.pos) is not None:
                                mods = pygame.key.get_mods()
                                args = []
                                if mods & KMOD_SHIFT:
                                    args += ["queue_order"]
                                if mods & KMOD_CTRL:
                                    args += ["imperative"]
                                self.cmd_default(*args)
                    elif e.type == MOUSEBUTTONUP:
                        if e.button == 1: # left mouse button
                            if self.mouse_select_origin == e.pos:
                                if self.grid_view.object_from_mousepos(e.pos):
                                    self.cmd_command_unit()
                            elif self.mouse_select_origin:
                                self.group = self.grid_view.units_from_mouserect(self.mouse_select_origin, e.pos)
                                self.say_group()
                            self.mouse_select_origin = None
                elif e.type == MOUSEBUTTONDOWN:
                    if e.button == 1: # left mouse button
                        self.cmd_fullscreen()
            except SystemExit:
                sys.exit()
            except:
                exception("error in pygame.event.get() loop")

    def queue_srv_event(self, *e):
        self._srv_queue.put(e)

    def _process_srv_events(self):
        if not self._srv_queue.empty():
            e = self._srv_queue.get()
            self._process_srv_event(*e)

    def loop(self):
        from clientserver import ConnectionAbortedError # TODO: remove the cyclic dependencies
        set_game_mode(True)
        pygame.event.clear()
        self.next_update = time.time()
        self.end_loop = False
        while not self.end_loop:
            try:
                self._ask_for_update_if_needed()
                self._remind_server_if_needed()
                self._animate_objects()
                self._process_events()
                self._process_srv_events()
                voice.update() # XXX useful for SAPI
                time.sleep(.01)
            except SystemExit:
                raise
            except ConnectionAbortedError:
                raise
            except:
                exception("error in clientgame loop")
        set_game_mode(False)

    mode = None
    indexunite = -1

    # keyboard

    def load_bindings(self, s):
        # Important: the modified key bindings (Ctrl, Shift, Alt) must be
        # before the other ones:
        def nb_modifiers(o):
            return len(o[0])
        self.bindings = []
        defines = []
        s = re.sub("(?m);.*$", "", s) # remove comments
        s = re.sub("(?m)^[ \t]*$\n", "", s) # remove empty lines
        s = re.sub(r"(?m)\\[ \t]*$\n", " ", s) # join lines ending with "\"
        for line in s.split("\n"):
            for p, s in defines:
                # no alphanumeric character (or the underscore)
                # before or after the identifier
                line = re.sub(r"(?<!\w)%s(?!\w)" % p, s, line)
            if line.find("#define ") == 0:
                words = line.strip().split(" ", 2)
                defines.append([words[1], words[2]])
            elif line.find(":") != -1:
                words = line.strip().split(":")
                try:
                    e, c = words
                    # keyboard event
                    e = e.split()
                    mods = [getattr(pygame.locals, "KMOD_" + m)
                            for m in e[:-1]]
                    key = getattr(pygame.locals, "K_" + e[-1])
                    # command
                    c = c.split()
                    if len(c) > 0:
                        cmd = c[0]
                        args = c[1:]
                    else:
                        warning("line ignored in bindings.txt: %s", line)
                        continue
                    # if the same key combination exists, remove it
                    for i, b in enumerate(self.bindings):
                        if b[:2] == [mods, key]:
                            del self.bindings[i]
                    self.bindings.append([mods, key, cmd, args])
                except AttributeError:
                    warning("line ignored in bindings.txt: %s", line)
                    continue
            elif line:
                warning("line ignored in bindings.txt: %s", line)
        # (without this, ctrl F2 would not work because of the unsorted list)
        self.bindings.sort(key=nb_modifiers, reverse=True)

    def _execute_order_shortcut(self, e):
        for o in self.orders():
            first_unit = self.dobjets[self.group[0]].model
            if order_shortcut(o, first_unit) == e.unicode:
                self._select_order(o)
                if order_args(o, first_unit) == 0:
                    self.cmd_validate()
        self.shortcut_mode = False

    def _execute_typing(self, event):
        if event.key in [pygame.K_LSHIFT, pygame.K_RSHIFT]:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            voice.item([self.typing_buffer])
            return getattr(self, "_finished_typing_%s" %
                self.typing_kind)(self.typing_buffer)
        elif event.key == pygame.K_ESCAPE:
            self._reset_typing()
        elif event.key == pygame.K_BACKSPACE:
            self.typing_buffer = self.typing_buffer[:-1]
            voice.item(string_to_msg(self.typing_buffer, self.typing_spell))
        elif re.match(self.typing_pattern, event.unicode) != None:
            try:
                c = event.unicode.encode("ascii") # telnetlib doesn't like unicode
                self.typing_buffer += c
                voice.item(string_to_msg(c) + [9999] +
                string_to_msg(self.typing_buffer, self.typing_spell))
            except:
                warning("error reading character from keyboard")
                voice.item([1003, 9999] + string_to_msg(s, spell))
        else:
            voice.item([1003, 9999] + string_to_msg(self.typing_buffer,
                self.typing_spell))

    def _reset_typing(self):
        self.typing_mode = False
        self.typing_buffer = ""
        self.typing_kind = ""
        self.typing_pattern = ""
        self.typing_spell = False

    def _launch_binding_if_event(self, e, mods, key, cmd, args=()):
        if e.key == key:
            mod_ok = True
            for mod in mods:
                mod_ok = mod_ok and ((e.mod & mod) != 0)
            if mod_ok:
                try:
                    command = getattr(self, "cmd_" + cmd)
                except AttributeError:
                    warning("error in bindings.txt: '%s' is not a command",
                            cmd)
                command(*args)
                return True
        return False

##    def execute_keydown_event(self, e):
##        cmd_args = self.keydown_event_command(e)
##        if cmd_args is not None:
##            cmd, args = cmd_args
##            cmd = getattr(self, "cmd_" + cmd)
##            cmd(*args)
##
##    def keydown_event_command(self, e):
##        for mods, key, cmd, args in self.bindings:
##            if e.key == key:
##                mod_ok = True
##                for mod in mods:
##                    mod_ok = mod_ok and ((e.mod & mod) != 0)
##                if mod_ok:
##                    if hasattr(self, "cmd_" + cmd):
##                        return cmd, args
##                    else:
##                        warning("error in bindings.txt: '%s' is not a command", cmd)
##                    break

    #

    immersion = False

    def cmd_immersion(self):
        if not self.immersion:
            self.toggle_immersion()

    def toggle_immersion(self):
        self.immersion = not self.immersion
        if self.immersion:
            self.cmd_unit_status()
            voice.item([4211])
        else:
            voice.item([4212])
        self.follow_mode = self.immersion

    def cmd_escape(self):
        if self.order:
            voice.item([4048])
            self.order = None
        elif self.immersion:
            self.toggle_immersion()
        elif self.zoom_mode:
            self.cmd_toggle_zoom()

    def _delete_object(self, _id):
        self.dobjets[_id].stop()
        del self.dobjets[_id]
        if _id in self.group:
            self.group.remove(_id)

    def update_fog_of_war(self):
        # updates dobjets (the dictionary of view objects)
        
        # add or update objects
        for m in self.memory:
            if m.id in self.dobjets and not self.dobjets[m.id].is_memory:
                self._delete_object(m.id) # memory will replace perception
            if m.id not in self.dobjets:
                self.dobjets[m.id] = EntityView(self, m)
                if self.target and m.id == self.target.id: # keep target
                    self.target = self.dobjets[m.id]
            else:
                self.dobjets[m.id].model = m
        for m in self.perception:
            if m.id not in self.dobjets:
                if self.player.is_an_enemy(m) or \
                   getattr(m, "resource_type", None) is not None:
                    self.scout_info.add(m.place)
            elif self.dobjets[m.id].is_memory:
                self._delete_object(m.id) # perception will replace memory
            if m.id not in self.dobjets:
                self.dobjets[m.id] = EntityView(self, m)
                if self.target and m.id == self.target.id: # keep target
                    self.target = self.dobjets[m.id]
            else:
                self.dobjets[m.id].model = m

        # remove missing objects
        pm = set(o.id for o in self.memory)
        pm.update(o.id for o in self.perception)
        for i in self.dobjets.keys():
            if i in pm:
                continue
            self._delete_object(i)
            if self.target and i == self.target.id:
                self.target = None
        if VERSION[-4:] == "-dev":
            for m in self.perception.union(self.memory):
                if m.place is None:
                    warning("%s.model is in memory or perception "
                            "and yet its place is None", m.type_name)

    def direction_to_msg(self, o):
        x, y = self.place_xy
        d = distance(x, y, o.x, o.y)
        if d < self.square_width / 3 / 2:
            return [156] # "at the center"
        s = direction_to_msgpart(math.degrees(angle(x, y, o.x, o.y, 0)))
        if s == 69:
            return [116] # to the east (special case, in French)
        if s == 70:
            return [117] # to the west (special case, in French)
        return [108, s] # "to the" + direction

    # immersive mode

    previous_compass = None

    def say_compass(self):
        s = direction_to_msgpart(self.o)
        if s != self.previous_compass:
            voice.item([s])
            self.previous_compass = s

    def cmd_rotate_left(self):
        if self.group:
            self.dobjets[self.group[0]].o += 45
            self.o += 45
            self.say_compass()
            psounds.update()

    def cmd_rotate_right(self):
        if self.group:
            self.dobjets[self.group[0]].o -= 45
            self.o -= 45
            self.say_compass()
            psounds.update()

    # menu monitor

    @staticmethod
    def _get_relevant_menu(menu):
        _m = menu[:]
        # TODO: use a "is_relevant" attribute
        # (when client side orders are objects)
        for x in ["stop",
                  "cancel_training", "cancel_upgrading", "cancel_building",
                  "mode_offensive", "mode_defensive",
                  "load", "load_all", "unload", "unload_all"]:
            if x in _m:
                _m.remove(x)
        return _m

    def _menu_has_increased(self, type_name, menu):
        for i in self._get_relevant_menu(menu):
            if i not in self.previous_menus[type_name]:
                return True
        return False

    def _remember_menu(self, type_name, menu):
        for i in self._get_relevant_menu(menu):
            if i not in self.previous_menus[type_name]:
                self.previous_menus[type_name].append(i)

    def _send_menu_alert_if_needed(self, type_name, menu, title):
        if type_name not in self.previous_menus:
            self.previous_menus[type_name] = []
        elif self._menu_has_increased(type_name, menu):
            voice.info([4223] + title + [4224]) # "menu of... changed"
        self._remember_menu(type_name, menu)

    def send_menu_alerts_if_needed(self):
        done = []
        for u in self.player.units:
            u = EntityView(self, u)
            if u.type_name not in done:
                self._send_menu_alert_if_needed(u.type_name, u.strict_menu, u.short_title)
                done.append(u.type_name)

    def summary(self, group):
        def remove_duplicates(l):
            m = []
            for i in l:
                if i not in m:
                    m.append(i)
            return m
        types = remove_duplicates(group) # set() would lose the order
        result = []
        for t in types:
            if t == types[-1] and len(types) > 1:
                result += [23] # "... and ..."
            elif t != types[0]:
                result += [9998]
            result += nb2msg(group.count(t)) + t
        return result

    def place_summary(self, place, me=True, zoom=None):
        enemies = []
        allies = []
        units = []
        resources = []
        for obj in self.dobjets.values():
            if not obj.is_in(place):
                continue
            if zoom and not zoom.contains(obj):
                continue
            if self.player.is_an_enemy(obj.model):
                enemies.append(obj.short_title)
            if obj.model.player in self.player.allied and not obj.model in self.player.units:
                allies.append(obj.short_title)
            if obj.model in self.player.units:
                units.append(obj.short_title)
            if getattr(obj.model, "resource_type", None) is not None:
                resources.append(obj.short_title)
        result = []
        if enemies:
            result += [9998] + self.summary(enemies) + [88]
        if me and allies:
            result += [9998] + self.summary(allies) + [4286]
        if me and units:
            result += [9998] + self.summary(units)
        if resources:
            result += [9998] + self.summary(resources)
        return result

    def say_group(self, prefix=[]):
        self.update_group()
        if len(self.group) == 1:
            u = self.dobjets[self.group[0]]
            # "You control footman 1"
            voice.item(prefix + [138] + u.ext_title + u.orders_txt)
        elif len(self.group) > 1:
            u = self.dobjets[self.group[0]]
            group = [self.dobjets[x].short_title for x in self.group
                     if x in self.dobjets]
            voice.item(prefix + [138] + self.summary(group) + u.orders_txt)
        else:
            voice.item(prefix + [4205]) # no unit controlled

    def tell_enemies_in_square(self, place):
        enemies = [x.short_title for x in self.dobjets.values()
                   if x.is_in(place) and self.player.is_an_enemy(x.model)]
        if enemies:
            voice.info(self.summary(enemies) + [88, 107] + place.title) # ... "ennemi" "en" ...

    def units_alert(self, units, msg_end):
        places = set([x[1] for x in units if x[1] is not None])
        for place in places:
            units_in_place = [x[0] for x in units if x[1] is place]
            s = self.summary(units_in_place)
            if s:
                voice.info(s + msg_end + [107] + place.title)
        while units:
            units.pop()

    previous_unit_attacked_alert = None

    previous_scout_info = None

    def scout_info_if_needed(self):
        if self.scout_info and (self.previous_scout_info is None or
                time.time() > self.previous_scout_info + 10):
            for place in self.scout_info:
                s = self.place_summary(place, me=False)
                if s:
                    voice.info(s + [107] + place.title)
            self.scout_info = set()
            self.previous_scout_info = time.time()

    previous_units_alert = None

    def units_alert_if_needed(self, place=None):
        if (self.neutralized_units or self.lost_units) and \
           (self.previous_units_alert is None
                or time.time() > self.previous_units_alert + 10):
            self.units_alert(self.neutralized_units, [145])
            self.units_alert(self.lost_units, [146])
            if place:
                self.tell_enemies_in_square(place) # if lost fight
            self.previous_units_alert = time.time()

    previous_squares_alert = None

    def squares_alert_if_needed(self):
        if self.alert_squares and (self.previous_squares_alert is None or
           time.time() > self.previous_squares_alert + 10):
            titles = sorted([sq.title for sq, t in self.alert_squares.items()
                             if time.time() < t + 5]) # recent attacks only
            if len(titles) > 1:
                titles.insert(-1, [23]) # "and"
            if titles:
                voice.info(sum(titles, [152, 107])) # "alert in..."
                self.previous_squares_alert = time.time()
            self.alert_squares = {}

    #

    previous_group = None

    def send_order(self, order, target, args):
        queue_order = int("queue_order" in args)
        imperative = int("imperative" in args)
        # send the order only to the concerned members of the group
        # (to avoid (precedently) unnecessary "order impossible" alerts
        #  or (now) a "wrong order" warning,
        #  and for the assertion in _group_has_enough_mana() in worldunit.py)
        if order == "default":
            g = self.group
        else:
            g = [uid for uid in self.group if order in self.dobjets[uid].menu]
        if g != self.previous_group: # to save bandwidth
            self.server.write_line("control " + group.encode(g))
            # make a copy to make sure that it is not modified later
            self.previous_group = g[:]
        if target is not None:
            order = "%s %s" % (order, target)
        self.server.write_line("order %s %s %s" %
                               (queue_order, imperative, order))

    @property
    def ui_target(self):
        if self.target is not None:
            return self.target
        else:
            if self.zoom_mode:
                return self.zoom
            else:
                return self.place

    _previous_order = None

    def cmd_validate(self, *args):
        if not self.group:
            voice.item([4205]) # no unit controlled
        elif self.order is None: # nothing to validate
            self.cmd_command_unit()
        elif self.an_order_not_requiring_a_target_is_selected:
            self.send_order(self.order, None, args)
            voice.item(order_title(self.order)) # confirmation
            self._previous_order = self.order
        elif self.an_order_requiring_a_target_is_selected:
            if self.order not in self.orders():
                # the order is not in the menu anymore
                psounds.play_stereo(sounds.get_sound(1029)) # hostile sound
            elif self.ui_target.id is not None:
                self.send_order(self.order, self.ui_target.id, args)
                # confirmation
                voice.item(order_title(self.order) + self.ui_target.title)
                self._previous_order = self.order
        self.order = None

    def _say_default_confirmation(self):
        # If the group contains different units with different default orders,
        # tell the various default orders.
        # For example, if the target is a goldmine and the group contains
        # workers and soldiers, then the interface will say:
        # "exploit a goldmine, move to a goldmine".
        msgs = []
        for u in self.group:
            if u in self.dobjets:
                order = self.dobjets[u].model.get_default_order(self.ui_target.id)
                if order is not None:
                    msg = order_title(order) + self.ui_target.title
                    if msg not in msgs:
                        msgs.append(msg)
        confirmation = []
        for msg in msgs:
            confirmation += msg + [9998]
        if confirmation:
            voice.item(confirmation)
        else:
            voice.item([1029]) # hostile sound

    def cmd_default(self, *args):
        if not self.group:
            voice.item([4205]) # no unit controlled
        elif self.ui_target.id is not None: # XXX useful?
            self.send_order("default", self.ui_target.id, args)
            self._say_default_confirmation()
        self.order = None

    def cmd_unit_status(self):
        self.say_group(self.place.title)
        if self.group:
            self.follow_mode = True
            self._follow_if_needed()

    def cmd_help(self, incr):
        incr = int(incr)
        voice.item(help_msg("game", incr))

    def _minimap_stereo(self, place):
        # TODO: avoid arbitrary flattening_factor and 6.0 (zoom level?)
        # Maybe the aim is to have a minimap with every sound audible enough.
        # So if at the same place the volume is minimap max, if very far the
        # volume is minimap min.
        x, y = self.coords_in_map(place)
        flattening_factor = 2.0
        xc, yc = self.coords_in_map(self.place)
        dx = (x - xc) * 6.0 / (self.xcmax + 1)
        dy = (y - yc) * 6.0 / (self.ycmax + 1) / flattening_factor
        return stereo(0, 0, dx, dy, 90)

    def launch_alert(self, place, sound):
        psounds.play_stereo(sounds.get_sound(sound), vol=self._minimap_stereo(place), limit=ALERT_LIMIT)

    def srv_alert(self, s):
        id_place, sound = s.split(",")
        place = self.player.get_object_by_id(int(id_place))
        self.launch_alert(place, int(sound))

    def cmd_unit_hp_status(self):
        if len(self.group) == 1:
            u = self.dobjets[self.group[0]]
            voice.item(u.description)

    follow_mode = False

    def _follow_if_needed(self):
        self.update_group()
        if self.follow_mode and self.group and not self.an_order_requiring_a_target_is_selected:
            if self.zoom_mode:
                if not self.zoom.contains(self.dobjets[self.group[0]]):
                    self.zoom.move_to(self.dobjets[self.group[0]])
                    if not voice.channel.get_busy(): # low priority: don't interrupt
                        self.zoom.say()
            elif not self.dobjets[self.group[0]].is_in(self.place):
                self.move_to_square(self.dobjets[self.group[0]].place)
                if not voice.channel.get_busy(): # low priority: don't interrupt
                    voice.item(self.place.title)
                if self.immersion:
                    self.target = None # unselect current object

    def units(self, even_if_no_menu=True, sort=False):
        def short_title_and_number(o):
            return (o.short_title, o.number)
        result = [self.dobjets[u.id] for u in self.player.allied_control_units if
             (even_if_no_menu or
              u.can_train or u.can_upgrade_to or
              u.orders or
              u.basic_abilities or
              u.id in self.dobjets and self.dobjets[u.id].menu)
             and not getattr(u, "is_inside", False)
             and u.id in self.dobjets]
        if sort:
            result.sort(key=short_title_and_number)
        return result

##    def srv_delunit(self, s):
##        iu = int(s)
##        for o in self.group[:]:
##            if o == iu:
##                self.group.remove(o)
##                if not self.group:
##                    if self.immersion:
##                        self.toggle_immersion()
##                break

    # select unit

    def update_group(self):
        self.group = [u for u in self.group if u in self.dobjets
                      and (self.dobjets[u].player is self.player
                           or self.dobjets[u].player in self.player.allied_control)]

    def _regroup(self, portion, types, local, idle, unused__even_if_no_menu):
        self.update_group()
        if self.group:
            initial_unit = self.dobjets[self.group[0]]
            if initial_unit.is_in(self.place):
                local_place = self.place
            else:
                local_place = initial_unit.place
            if not types:
                types = []
                for _id in self.group:
                    if self.dobjets[_id].type_name not in types:
                        types.append(self.dobjets[_id].type_name)
            self.group = []
            units = self.units()
            for t in types:
                m = [x.id for x in units if x.type_name == t and \
                     (not local or self.zoom_mode and self.zoom.contains(x)
                      or not self.zoom_mode and x.is_in(local_place)) and \
                     (not idle or not x.orders)]
                self.group += m[: len(m) / portion]
            if initial_unit.id not in self.group \
               and initial_unit.type_name in types:
                if self.group:
                    self.group.pop()
                self.group.append(initial_unit.id)
        self.say_group()

    def cmd_group(self, portion, *args):
        portion = int(portion)
        self._regroup(portion, *self._arrange(args))

    def cmd_ungroup(self):
        if len(self.group) > 1:
            self.group = [self.group[0]]
        self.say_group()

    def command_unit(self, unit, silent=False):
        if not silent:
            voice.item(unit.ext_title + unit.orders_txt + [4202]) # "awaiting your orders"
        self.group = [unit.id]

    def cmd_command_unit(self):
        if self.target in self.units():
            self.command_unit(self.target)

    def _select_unit(self, inc, types, local, idle, even_if_no_menu, silent=False):
        units = self.units(even_if_no_menu=even_if_no_menu, sort=True)
        if types:
            units = [x for x in units if x.type_name in types]
        if local:
            if self.zoom_mode:
                units = [x for x in units if self.zoom.contains(x)]
            else:
                units = [x for x in units if x.is_in(self.place)]
        if idle:
            units = [x for x in units if not x.orders]
        if not units:
            self.group = []
            return
        sel = -1 # if next (+1) => 0, if previous (-1) => -2 < 0 => last
        for i, u in enumerate(units):
            if u.id in self.group:
                sel = i
                break
        sel += inc
        if sel < 0:
            sel = len(units) - 1
        if sel >= len(units):
            sel = 0
        self.command_unit(units[sel], silent=silent)
        self.order = None

    def _arrange(self, args):
        local = "local" in args
        idle = "idle" in args
        even_if_no_menu = "even_if_no_menu" in args
        keyboard_types = [x for x in args if x not in ("local", "idle", "even_if_no_menu")]
        types = [x for x in style.classnames()
                 if style.has(x, "keyboard")
                 and style.get(x, "keyboard")[0] in keyboard_types]
        return types, local, idle, even_if_no_menu

    def cmd_select_unit(self, inc, *args):
        inc = int(inc)
        self._select_unit(inc, *self._arrange(args))

    def cmd_select_units(self, *args):
        self._select_unit(1, *(list(self._arrange(args)) + [True]))
        self._regroup(1, *self._arrange(args))

    # recallable groups

    def cmd_set_group(self, name, *args):
        self.groups[name] = set(self.group)
        voice.item(["ok"])

    def cmd_append_group(self, name, *args):
        if name not in self.groups:
            self.groups[name] = set()
        self.groups[name].update(self.group)
        voice.item(["ok"])

    def cmd_recall_group(self, name, *args):
        if name not in self.groups:
            self.groups[name] = set()
        self.group = self.groups[name]
        self.say_group()

    # select order

    order = None

    def orders(self):
        menu = []
        for u in self.group:
            if u in self.dobjets: # useful?
                for o in self.dobjets[u].menu:
                    if o not in menu:
                        menu.append(o)
        # sort the menu by index
        menu.sort(key=order_index)
        return menu

    @property
    def an_order_not_requiring_a_target_is_selected(self):
        return self.order and self.group and order_args(self.order, self.dobjets[self.group[0]].model) == 0

    @property
    def an_order_requiring_a_target_is_selected(self):
        return self.order and self.group and order_args(self.order, self.dobjets[self.group[0]].model)

    def _select_order(self, order):
        self.order = order
        # say the new current order
        msg = order_title(self.order) + order_comment(self.order,
            self.dobjets[self.group[0]].model) # "requires..."
                    # XXX actually group[0] is not necessary the right
                    # one but it is only used to retrieve the world object
        if order_args(self.order, self.dobjets[self.group[0]].model) == 0:
            msg += [9998, 4064] # the order must be validated
        else:
            msg += [9998, 4067] # the order will be validated when the parameter is validated
        voice.item(msg)

    def cmd_select_order(self, inc):
        inc = int(inc)
        orders = self.orders() # do this once (can take a long time)
        # if no menu then do nothing
        if not orders:
            voice.item([0]) # "nothing!"
            self.order = None
            return
        # select the next/previous order
        if self.order is None:
            index = -1
        else:
            try:
                index = orders.index(self.order)
            except ValueError: # order not found
                index = -1
        index += inc
        if index < 0:
            index = len(orders) - 1
        elif index >= len(orders):
            index = 0
        self._select_order(orders[index])

    def cmd_order_shortcut(self):
        if self.group:
            msg = []
            first_unit = self.dobjets[self.group[0]].model
            for o in self.orders():
                shortcut = order_shortcut(o, first_unit)
                if shortcut:
                    msg += [str(shortcut)] + order_title(o) + [9998]
            if msg:
                self.shortcut_mode = True
                voice.item(msg)
                return
        voice.item([1029]) # hostile sound

    def cmd_do_again(self, *args):
        if self._previous_order is not None and self.group:
            self._select_order(self._previous_order)
            if "now" in args and \
               order_args(self.order, self.dobjets[self.group[0]].model) == 0:
                args = [a for a in args if a in ("queue_order", "imperative")]
                self.cmd_validate(*args)

    # select square

    @property
    def place_xy(self):
        return self.place.x / 1000.0, self.place.y / 1000.0

    @property
    def xcmax(self):
        return self.server.player.world.nb_columns - 1

    @property
    def ycmax(self):
        return self.server.player.world.nb_lines - 1

    def coords_in_map(self, square):
        if square is not None:
            return square.col, square.row
        return -1, -1

    def move_to_square(self, square):
        if self.place is not square and self.coords_in_map(square) != (-1, -1):
            self.place = square
            self._silence_square()
            self.display()
            if get_fullscreen():
                pygame.mouse.set_pos(self.grid_view.active_square_center_xy_coords())
                # ignore the mouse motion event (it's not directly from the player)
                pygame.event.clear(pygame.MOUSEMOTION)

    def _silence_square(self):
        for o in self.dobjets.values():
            if not o.is_in(self.place):
                o.stop()
        sound_stop(stop_voice_too=False) # cut the long nonlooping environment sounds

    def square_postfix(self, place):
        postfix = []
        if place in self.scouted_squares:
            if place.high_ground: postfix += [4314] # "plateau"
        elif place in self.scouted_before_squares:
            if place.high_ground: postfix += [4314] # "plateau"
            postfix += [4209] # "in the fog"
        else:
            postfix += [4208] # "unknown"
        return postfix
        
    def say_square(self, place, prefix=[]):
        if place is None:
            return
        postfix = self.square_postfix(place)
        voice.item(prefix + place.title + postfix + self.place_summary(place))

    def _select_and_say_square(self, square, prefix=[]):
        self.move_to_square(square)
        self.target = None
        self.say_square(square, prefix)
        self.follow_mode = False

    def _compute_move(self, dxc, dyc):
        xc, yc = self.coords_in_map(self.place)
        xc += dxc
        if xc < 0:
            xc = self.xcmax
        if xc > self.xcmax:
            xc = 0
        yc += dyc
        if yc < 0:
            yc = self.ycmax
        if yc > self.ycmax:
            yc = 0
        return self.server.player.world.grid[(xc, yc)]

    def _get_prefix_and_collision(self, new_square, dxc, dyc):
        if new_square is self.place:
            return style.get("parameters", "no_path_in_this_direction"), True
        if self.place not in self.scouted_before_squares:
            return [], False
        exits = [o for o in self.dobjets.values() if o.is_in(self.place)
                 and self.is_selectable(o)
                 and o.is_an_exit
                 and not o.is_blocked(self.player)]
        prefix = style.get("parameters", "no_path_in_this_direction")
        collision = True
        xc, yc = self.coords_in_map(self.place)
        x, y = (xc + .5) * self.square_width, (yc + .5) * self.square_width
        for o in exits:
            if dxc == 1 and o.x > x or \
               dxc == -1 and o.x < x or \
               dyc == 1 and o.y > y or \
               dyc == -1 and o.y < y:
                prefix = o.when_moving_through
                collision = False
                break
        return prefix, collision

    def cmd_select_square(self, dxc, dyc, *args):
        dxc = int(dxc)
        dyc = int(dyc)
        fly = "no_collision" in args
        if self.immersion:
            if (dxc, dyc) == (-1, 0):
                self.cmd_rotate_left()
            elif (dxc, dyc) == (1, 0):
                self.cmd_rotate_right()
        elif self.zoom_mode:
            self.zoom.move(dxc, dyc)
            self.zoom.select()
            self.zoom.say()
        elif self.place is not None:
            new_square = self._compute_move(dxc, dyc)
            prefix, collision = self._get_prefix_and_collision(new_square, dxc,
                                                               dyc)
            if fly or not collision:
                self.move_to_square(new_square)
            self._select_and_say_square(self.place, prefix)

    def _select_square_from_list(self, increment, squares):
        if squares:
            if self.immersion:
                self.toggle_immersion()
            if self.zoom_mode:
                self.cmd_toggle_zoom()
            _squares = list(squares) # make a copy
            if self.place not in _squares:
                _squares.append(self.place)
            _squares.sort()
            index = _squares.index(self.place) + int(increment)
            if index < 0:
                index = len(_squares) - 1
            elif index == len(_squares):
                index = 0
            self._select_and_say_square(_squares[index])
        else:
            voice.item([0]) # "nothing!"

    def cmd_select_scouted_square(self, increment):
        self._select_square_from_list(increment, self.scouted_squares)

    def cmd_select_conflict_square(self, increment):
        enemy_units = [o for o in self.dobjets.values()
                       if o.player and o.player.is_an_enemy(self.player)]
        conflict_squares = []
        for u in enemy_units:
            if u.place not in conflict_squares:
                conflict_squares.append(u.place)
        self._select_square_from_list(increment, conflict_squares)

    def cmd_select_unknown_square(self, increment):
        unknown_squares = [p for p in self.player.world.squares
                           if p not in self.scouted_before_squares]
        self._select_square_from_list(increment, unknown_squares)

    def cmd_select_resource_square(self, increment):
        resource_squares = []
        for o in self.dobjets.values():
            if getattr(o, "resource_type", None) is not None:
                if o.place not in resource_squares:
                    resource_squares.append(o.place)
        self._select_square_from_list(increment, resource_squares)

    def set_obs_pos(self):
        if self.place is None: # first position
            if self.units():
                self._select_and_say_square(self.units(sort=True)[0].place)
        self._follow_if_needed()
        if self.immersion and self.group and self.group[0] in self.dobjets:
            self.x = self.dobjets[self.group[0]].x
            self.y = self.dobjets[self.group[0]].y
            self.o = self.dobjets[self.group[0]].o
        elif self.zoom_mode:
            self.x, self.y = self.zoom.obs_pos() 
        else:
            xc, yc = self.coords_in_map(self.place)
            self.x = self.square_width * (xc + .5)
            self.y = self.square_width * (yc + 1/8.0)
##            self.x = place.x
##            self.y = place.ymin + self.square_width / 8.0
##            self.x = self.square_width / 2.0
##            self.y = self.square_width / 8.0 # self.y = 0 ?
            if self.place not in self.scouted_squares:
                self.y -= self.square_width # lower sounds if fog of war
        psounds.update()

    def cmd_toggle_zoom(self):
        if not self.place:
            return
        self.zoom_mode = not self.zoom_mode
        if self.zoom_mode:
            self.zoom = Zoom(self)
            voice.item([4318, 4263]) # is now on
        else:
            voice.item([4318, 4264]) # is now off

    # display

    def display(self):
        if get_screen() is None:
            return # this might allow some machines to work without any display
        get_screen().fill((0, 0, 0))
        if get_fullscreen():
            self.grid_view.display()
            if self.mouse_select_origin and self.mouse_select_origin != pygame.mouse.get_pos():
                x, y = self.mouse_select_origin
                x2, y2 = pygame.mouse.get_pos()
                pygame.draw.rect(get_screen(), (255, 255, 255), (min(x, x2), min(y, y2), abs(x - x2), abs(y - y2)), 1)
        else:
            screen_render("[Ctrl + F2] display.", (5, 45))
        self.display_tps()
        screen_render_subtitle()
        pygame.display.flip()

    def cmd_fullscreen(self):
        toggle_fullscreen()

    # resources

    @property
    def resources(self):
        return [int(x / PRECISION) for x in self.server.player.resources]

    @property
    def available_food(self):
        return self.server.player.available_food

    @property
    def used_food(self):
        return self.server.player.used_food

    def cmd_resource_status(self, resource_type):
        resource_type = int(resource_type)
        voice.item(nb2msg(self.resources[resource_type]) + style.get(
            "parameters", "resource_%s_title" % resource_type))

    def cmd_food_status(self):
        voice.item(nb2msg(self.available_food, gender="f") + [137, 2011] +
                   nb2msg(self.used_food))
        # other possibility: available_food + [137,133,2011] + food

    def send_msg_if_playing(self, msg, update_type=None):
        # say only if game started
        if self.last_virtual_time != 0:
            voice.info(msg, expiration_delay=1.5, update_type=update_type)

    _previous_resources = None
    _previous_available_food = 0
    _previous_used_food = 0

    def send_resource_alerts_if_needed(self):
        if self._previous_resources is None:
            self._previous_resources = self.resources[:]
        for i, r in enumerate(self.resources):
            r = int(r)
            if r != self._previous_resources[i]:
                self._previous_resources[i] = r
                if must_be_said(r):
                    self.send_msg_if_playing(nb2msg(r) + style.get(
                        "parameters", "resource_%s_title" % i),
                        update_type="resource_%s" % i)
        if self.available_food != self._previous_available_food or \
           self.used_food > self._previous_used_food or \
           (self.used_food < self._previous_used_food and
            self._previous_used_food == self.available_food):
            if 0 <= self.available_food - self.used_food <= \
               self.available_food * .20:
                self.send_msg_if_playing(nb2msg(self.available_food, gender="f")
                                         + [137, 2011]
                                         + nb2msg(self.used_food),
                                         update_type="food")
            self._previous_available_food = self.available_food
            self._previous_used_food = self.used_food
