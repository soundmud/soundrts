import math
import Queue
import re
import sys
import time

import pygame
from pygame.locals import KEYDOWN, QUIT, USEREVENT, KMOD_ALT, MOUSEBUTTONDOWN, KMOD_SHIFT, KMOD_CTRL, MOUSEBUTTONUP, MOUSEMOTION

from clientgamegridview import GridView 
from clientgamefocus import Zoom
from clienthelp import help_msg
from clientmedia import voice, sounds, sound_stop, modify_volume, get_fullscreen, toggle_fullscreen, play_sequence
from lib.mouse import set_cursor
from clientmenu import Menu, input_string
from clientgameentity import EntityView
from clientgamenews import must_be_said
from clientgameorder import OrderTypeView, nb2msg_f
import config
from definitions import style, VIRTUAL_TIME_INTERVAL
from lib import chronometer as chrono
from lib import group
from lib.bindings import Bindings
from lib.log import debug, warning, exception
from lib.msgs import nb2msg, eval_msg_and_volume
from lib.nofloat import PRECISION
from version import IS_DEV_VERSION
from lib.sound import psounds, distance, angle, vision_stereo, stereo
from lib.screen import set_game_mode, screen_render, get_screen,\
    screen_render_subtitle
import msgparts as mp


# minimal interval (in seconds) between 2 sounds
ALERT_LIMIT = .5

# don't play events after this limit (in seconds)
EVENT_LIMIT = 3

BEEP_SOUND = mp.BEEP[0]
POSITIONAL_BEEP_SOUND = mp.POSITIONAL_BEEP[0]

def direction_to_msgpart(o):
    o = round(o / 45.0) * 45.0
    while o >= 360:
        o -= 360
    while o < 0:
        o += 360
    if o == 0:
        return mp.EAST
    elif o == 45:
        return mp.NORTHEAST
    elif o == 90:
        return mp.NORTH
    elif o == 135:
        return mp.NORTHWEST
    elif o == 180:
        return mp.WEST
    elif o == 225:
        return mp.SOUTHWEST
    elif o == 270:
        return mp.SOUTH
    elif o == 315:
        return mp.SOUTHEAST

def _get_relevant_menu(menu):
    _m = menu[:]
    for x in ["stop",
              "cancel_training", "cancel_upgrading", "cancel_building",
              "mode_offensive", "mode_defensive",
              "load", "load_all", "unload", "unload_all"]:
        if x in _m:
            _m.remove(x)
    return _m

def _remove_duplicates(l):
    m = []
    for i in l:
        if i not in m:
            m.append(i)
    return m

def load_palette():
    p = []
    with open("res/ui/editor_palette.txt", "U") as f:
        for s in f:
            s = s.strip()
            if s and not s.startswith(";"):
                if s.startswith("def"):
                    k = s.split()[1]
                    t = dict()
                    p.append((k, t))
                    t["style"] = k
                    t["water"] = False
                    t["ground"] = True
                    t["air"] = True
                    t["high_ground"] = False
                    t["meadows"] = 0
                    t["woods"] = (0, "75")
                    t["goldmines"] = (0, "150")
                    t["speed"] = (100, 100)
                    t["cover"] = (0, 0)
                else:
                    k = s.split()[0]
                    v = s.split()[1:]
                    if k in ["air", "ground", "water", "high_ground", "meadows"]:
                        v = int(v[0])
                    elif k == "style":
                        if v:
                            v = v[0]
                        else:
                            v = None
                    elif k in ["water", "ground", "air", "high_ground"]:
                        v = bool(v)
                    elif k in ["woods", "goldmines"]:
                        v = int(v[0]), v[1]
                    elif k in ["speed", "cover"]:
                        v = tuple(map(lambda x: int(float(x) * 100), v[:2]))
                    t[k] = v
    return p

##for k, v in load_palette():
##    print k
##    for kk, vv in v.items():
##        print " ", kk, vv


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
        self.lost_units = []
        self.neutralized_units = []
        self.new_enemy_units = []
        self.previous_menus = {}
        self.scout_info = set()
        self._known_resource_places = set()
        server.interface = self
        self.grid_view = GridView(self)
        self.set_self_as_listener()
        voice.silent_flush()
        self._srv_queue = Queue.Queue()
        self.scouted_squares = ()
        self.scouted_before_squares = ()
        self._bindings = Bindings()

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

    @property
    def world(self):
        return self.server.player.world

    _square_width = None
    
    @property
    def square_width(self):
        if self._square_width is None:
            self._square_width = self.world.square_width / 1000.0
        return self._square_width

    def _process_srv_event(self, *e):
        try:
            cmd = getattr(self, "srv_" + e[0])
        except AttributeError:
            warning("Not recognized: %s" % e[0])
        else:
            cmd(*e[1:])

    def srv_event(self, o, e):
        try:
            if hasattr(self, "next_update") and \
               time.time() > self.next_update + EVENT_LIMIT:
                return
            EntityView(self, o).notify(e)
        except:
            exception("problem during srv_event")


    def cmd_say(self):
        msg = input_string(msg=mp.ENTER_MESSAGE,
                           pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+=?!]$",
                           spell=False)
        if not msg:
            return
        voice.confirmation([self.player.client.login] + mp.SAYS + [msg])
        self.server.write_line("say %s" % msg)

    def cmd_say_players(self):
        msg = []
        for p in self.world.players:
            msg += p.name + mp.COMMA
        voice.item(msg)

    def srv_msg(self, s):
        voice.info(*eval_msg_and_volume(s))

    def srv_voice_important(self, s):
        voice.confirmation(*eval_msg_and_volume(s)) # remember the pressed key

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
            if self.order.cls.keyword == "build" and o.is_a_building_land:
                if o.is_an_exit:
                    p = .5
                else:
                    p = 0
        else:
            if self.player.is_an_enemy(o):
                p = .5
            elif o.qty > 0:
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
        return self.is_visible(o)

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
            voice.item(d + mp.COMMA + self.order.title, vg, vd)
        else:
            voice.item(*self.get_description_of(self.target))

    def get_description_of(self, o):
        if self.immersion:
            vg, vd = vision_stereo(self.x, self.y, o.x, o.y, self.o)
            return mp.POSITIONAL_BEEP + o.title \
                   + mp.AT2 + nb2msg(self.distance(o)) + mp.METERS \
                   + self.direction_to_msg(o) + o.description, vg, vd
        else:
            self.o = 90
            vg, vd = vision_stereo(self.x, self.y, o.x, o.y, self.o)
            return mp.POSITIONAL_BEEP + o.title \
                   + self.direction_to_msg(o) + o.description, vg, vd

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
            voice.item(mp.NOTHING)
            self.target = None

    # misc

    def cmd_objectives(self):
        msg = []
        if self.world.objective:
            msg += mp.OBJECTIVE + self.world.objective + mp.PERIOD
        if self.player.objectives:
            msg += mp.OBJECTIVE + mp.COMMA
            for o in self.player.objectives.values():
                msg += o.description + mp.COMMA
        voice.item(msg)

    def cmd_toggle_cheatmode(self):
        if self.server.allow_cheatmode:
            self.server.write_line("toggle_cheatmode")
            if self.player.cheatmode:
                voice.item(mp.CHEATMODE + mp.IS_NOW_OFF)
            else:
                voice.item(mp.CHEATMODE + mp.IS_NOW_ON)
        else:
            voice.item(mp.BEEP)

    _editor = False

    def _execute_command(self, cmd):
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
        elif cmd == "edit":
            self._editor = not self._editor
            if self._editor:
                self.player.cheatmode = True
                for p in self.world.players:
                    p.triggers = []
                self._bindings = Bindings()
                self._bindings.load(open("res/ui/editor_bindings.txt", "U").read(), self)
                voice.item(["editor"])
            else:
                voice.item(mp.BEEP)
        elif cmd == "sm":
            def next_available_filename(name):
                import os.path
                n = 0
                while os.path.exists(name % n):
                    n += 1
                return name % n
            self.world.save_map(next_available_filename("user/multi/editor%s.txt"))
        elif cmd.startswith("te "):
            delta = map(int, cmd.split(" ")[1:3])
            if self.place.toggle_path(*delta):
                voice.item(["path"])
            else:
                voice.item(["obstacle"])
        elif cmd.startswith("st "):
            pal = load_palette()
            name = cmd.split(" ")[1]
            if name in ["1", "-1"]:
                try:
                    i = [d for k, d in pal].index(self._editor_terrain) + int(name)
                    i %= len(pal)
                except:
                    i = 0
                self._editor_terrain = pal[i][1]
                voice.item([pal[i][0]])
            else:
                for k, d in pal:
                    if k == name:
                        self._editor_terrain = d
                        voice.item([name])
                        return
                voice.item(mp.BEEP)
        elif cmd == "at":
            d = self._editor_terrain
            p = self.place
            p.type_name = d["style"]
            self._terrain_loop_square = None # must update terrain audio background
            p.is_water = d["water"]
            p.is_ground = d["ground"]
            p.is_air = d["air"]
            p.high_ground = d["high_ground"]
            for p2 in p.strict_neighbors:
                if p.is_ground and p2.is_ground and p.high_ground == p2.high_ground:
                    p.ensure_path(p2)
                else:
                    p.ensure_nopath(p2)
            p.ensure_resources("goldmine", *d["goldmines"])
            p.ensure_resources("wood", *d["woods"])
            p.ensure_meadows(d["meadows"])
            p.terrain_speed = d["speed"]
            p.terrain_cover = d["cover"]
            if d["style"]:
                voice.item([d["style"]])
        elif cmd == "dti":
            self._must_display_target_info = not self._must_display_target_info
        elif cmd:
            cmd = re.sub("^a ", "add_units %s " % getattr(self.place, "name", ""), cmd)
            cmd = re.sub("^v$", "victory", cmd)
            self.server.write_line("cmd " + cmd)

    def cmd_cmd(self, *split_cmd):
        if self.server.allow_cheatmode:
            cmd = " ".join(split_cmd)
            self._execute_command(cmd)
        else:
            voice.item(mp.BEEP)

    def cmd_console(self):
        if self.server.allow_cheatmode:
            cmd = input_string(msg=mp.ENTER_COMMAND,
                               pattern="^[a-zA-Z0-9 .,'@#$%^&*()_+-=?!]$",
                               spell=False)
            if cmd is None:
                return
            self._execute_command(cmd)
        else:
            voice.item(mp.BEEP)

    def _next_player(self, player):
        players = self.world.players
        index = (players.index(player) + 1) % len(players)
        return players[index]

    def _change_player(self, new_player):
        new_player.client.login, self.server.player.client.login = self.server.player.client.login, new_player.client.login
        self.server.player.client = new_player.client
        self.server.player = new_player
        self.server.player.client = self.server
        self.update_fog_of_war()

    def cmd_change_player(self):
        if self.server.allow_cheatmode:
            self._change_player(self._next_player(self.player))
            voice.item(mp.YOU_ARE + self.player.name)
        else:
            voice.item(mp.BEEP)
        
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
        menu = Menu(mp.MENU, [
            (mp.CANCEL_GAME, self.gm_quit),
            (mp.SET_SPEED_TO_SLOW, self.gm_slow_speed),
            (mp.SET_SPEED_TO_NORMAL, self.gm_normal_speed),
            (mp.SET_SPEED_TO_FAST, self.gm_fast_speed),
            (mp.SET_SPEED_TO_FAST + nb2msg(4), self.gm_very_fast_speed),
            ])
#        if self.can_save():
#            menu.append(mp.SAVE, self.gm_save)
        menu.append(mp.CONTINUE_GAME, None)
        set_game_mode(False)
        menu.run()
        set_game_mode(True)

    already_asked_to_quit = False
    forced_quit = False

    def gm_quit(self):
        if self._editor:
            self.world.save_map("user/multi/editor_autosave.txt")
            self.srv_quit() # forced quit
            self.forced_quit = True
        elif not self.already_asked_to_quit:
            self.next_update = time.time() # useful if the game is paused
            self.server.write_line("quit")
            pygame.event.clear()
            self.already_asked_to_quit = True
        else:
            self.srv_quit() # forced quit
            self.forced_quit = True

    def _set_speed(self, speed):
        self.server.write_line("speed %s" % speed)
        self.speed = speed

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

    _bell_enabled = False
    _previous_nb_minutes = 0

    def cmd_toggle_talking_clock(self): # bell, in fact
        self._bell_enabled = not self._bell_enabled
        if self._bell_enabled:
            voice.item(mp.BELL + mp.IS_NOW_ON)
            self._previous_nb_minutes = int(self.last_virtual_time / 60)
        else:
            voice.item(mp.BELL + mp.IS_NOW_OFF)

    def _eventually_play_bell(self):
        nb_minutes = int(self.last_virtual_time / 60)
        if self._previous_nb_minutes != nb_minutes:
            psounds.play_stereo(sounds.get_sound(POSITIONAL_BEEP_SOUND))
            self._previous_nb_minutes = nb_minutes

    def cmd_say_time(self):
        m, s = divmod(int(self.last_virtual_time), 60)
        voice.item(nb2msg(m) + mp.MINUTES + nb2msg(s) + mp.SECONDS \
                   + mp.COMMA \
                   + mp.SPEED + ["%.1f" % self._get_relative_speed()])

    _must_play_tick = False

    _average_turn_duration = 0
    _previous_update_time = None

    def _play_tick(self):
        psounds.play_stereo(sounds.get_sound(POSITIONAL_BEEP_SOUND), vol=.1)

    def _record_update_time(self):
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / min(10.0, self.speed)
        nb_samples = max(1.0, 1.0 / interval)
        if self._previous_update_time is None:
            turn_duration = interval
        else:
            turn_duration = time.time() - self._previous_update_time
        self._average_turn_duration = (self._average_turn_duration * (nb_samples - 1) + turn_duration) / nb_samples
        self._previous_update_time = time.time()

    def _get_tps(self):
        try:
            return 1 / self._average_turn_duration
        except ZeroDivisionError:
            return 100

    @property
    def real_speed(self):
        return self._get_relative_speed()

    def _get_relative_speed(self):
        normal_speed_tps = 1 / (VIRTUAL_TIME_INTERVAL / 1000.0)
        return self._get_tps() / normal_speed_tps

    def cmd_toggle_tick(self):
        self._must_play_tick = not self._must_play_tick

    # loop

    def srv_voila(self, t, memory, perception, scouted_squares, scouted_before_squares, collision_debug):
        self.last_virtual_time = float(t) / 1000.0
        self.waiting_for_world_update = False

        self.memory = memory
        self.perception = perception
        self.scouted_squares = scouted_squares
        self.scouted_before_squares = scouted_before_squares
        self.collision_debug = collision_debug

        self.send_resource_alerts_if_needed()
        if self.previous_menus == {}:
            self.send_menu_alerts_if_needed() # init
        self.units_alert_if_needed()
        self.squares_alert_if_needed()
        self.scout_info_if_needed()

        self.update_fog_of_war()
        self.update_group()
        self.display()

        if self._bell_enabled:
            self._eventually_play_bell()
        if self._must_play_tick:
            self._play_tick()
        self._record_update_time()

    waiting_for_world_update = False

    def _ask_for_update(self):
        for player, order in self.server.get_orders():
            self.world.queue_command(player, order)
        self.world.queue_command(None, self.world.update)
        self.waiting_for_world_update = True
        interval = VIRTUAL_TIME_INTERVAL / 1000.0 / self.speed
        self.next_update = time.time() + interval

    def _time_to_ask_for_next_update(self):
        return not self.waiting_for_world_update and time.time() >= self.next_update

    _terrain_loop = None
    _terrain_loop_square = None

    def _animate_terrain(self):
        sq = self.place
        if sq and self._terrain_loop_square != sq:
            if self._terrain_loop and self._terrain_loop.is_playing():
                self._terrain_loop.stop()
            if sq not in self.scouted_squares and sq not in self.scouted_before_squares:
                return
            t = sq.type_name
            if t:
                st = style.get(t, "noise")
                if st:
                    if st[0] == "loop":
                        try:
                            volume = float(st[2])
                        except:
                            volume = 1
                        self._terrain_loop = psounds.play_loop(sounds.get_sound(st[1]), volume, sq.x/1000.0, sq.y/1000.0, -10)
            self._terrain_loop_square = sq

    previous_animation = 0

    def _animate_objects(self):
        if time.time() >= self.previous_animation + .1:
            chrono.start("animate")
            try:
                self.set_obs_pos()
            except:
                exception("couldn't set user interface position")
            for o in self.dobjets.values():
                try:
                    o.animate()
                except:
                    exception("couldn't animate object")
            try:
                self._animate_terrain()
            except:
                exception("couldn't animate terrain")
            self.previous_animation = time.time()
            chrono.stop("animate")

    def _process_fullscreen_mode_mouse_event(self, e):
        if e.type == MOUSEMOTION:
            square = self.grid_view.square_from_mousepos(e.pos)
            target = self.grid_view.object_from_mousepos(e.pos)
            if target is not None:
                if target != self.target:
                    self.target = target
                    self.say_target()
                    self.display()
                    if self.an_order_requiring_a_target_is_selected:
                        if self.order.cls.keyword == "build":
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
                        if self.order.cls.keyword == "build":
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

    def load_bindings(self, s):
        self._bindings.load(s, self)

    def _execute_order_shortcut(self, e):
        for o in self.orders():
            if o.shortcut == e.unicode:
                self._select_order(o)
                if o.nb_args == 0:
                    self.cmd_validate()
                return
        voice.item(mp.BEEP)

    def _process_events(self):
        # Warning: only sound/voice/keyboard events here, no server event.
        # Because a bad loop might occur when called from a function
        # waiting for a combat sound to end.
        for e in pygame.event.get():
            if e.type == USEREVENT:
                voice.update()
            elif e.type == USEREVENT + 1:
                psounds.update()
            elif e.type == QUIT:
                sys.exit()
            elif e.type == KEYDOWN:
                if self.shortcut_mode:
                    self._execute_order_shortcut(e)
                    self.shortcut_mode = False
                else:
                    try:
                        self._bindings.process_keydown_event(e)
                    except KeyError:
                        voice.item(mp.BEEP)
                    self.display() # for example when a new square is selected
            elif get_fullscreen():
                self._process_fullscreen_mode_mouse_event(e)

    def queue_srv_event(self, *e):
        self._srv_queue.put(e)

    def _process_srv_events(self):
        if not self._srv_queue.empty():
            e = self._srv_queue.get()
            self._process_srv_event(*e)

    def loop(self):
        from clientserver import ConnectionAbortedError
        set_game_mode(True)
        pygame.event.clear()
        self.next_update = time.time()
        self.end_loop = False
        while not self.end_loop:
            try:
                if 0 and IS_DEV_VERSION and not get_fullscreen():
                    # updated often (for total delay)
                    self.display()
                self.server.update()
                if self._time_to_ask_for_next_update() \
                   and self.server.orders_are_ready():
                    self._ask_for_update()
                self._animate_objects()
                self._process_events()
                self._process_srv_events()
                voice.update() # useful for SAPI
                time.sleep(.001)
            except SystemExit:
                raise
            except ConnectionAbortedError:
                raise
            except:
                exception("error in clientgame loop")
        set_game_mode(False)

    mode = None
    indexunite = -1

    immersion = False

    def cmd_immersion(self):
        if not self.immersion:
            self.toggle_immersion()

    def toggle_immersion(self):
        self.immersion = not self.immersion
        if self.immersion:
            self.cmd_unit_status()
            voice.item(mp.FIRST_PERSON_MODE)
        else:
            voice.item(mp.MAP_MODE)
        self.follow_mode = self.immersion

    def cmd_escape(self):
        if self.order:
            voice.item(mp.CANCEL)
            self.order = None
        elif self.immersion:
            self.toggle_immersion()
        elif self.zoom_mode:
            self.cmd_toggle_zoom()
        elif self.target:
            self._select_and_say_square(self.place)

    def _delete_object(self, _id):
        self.dobjets[_id].stop()
        del self.dobjets[_id]
        if _id in self.group:
            self.group.remove(_id)

    def _must_report_resource(self, m):
        if getattr(m, "resource_type", None) is not None \
           and m.place not in self._known_resource_places:
            self._known_resource_places.add(m.place)
            return True

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
                if self._must_report_resource(m):
                    self.scout_info.add(m.place)
            else:
                self.dobjets[m.id].model = m
        for m in self.perception:
            if m.id not in self.dobjets:
                if self.player.is_an_enemy(m):
                    self.new_enemy_units.append([EntityView(self, m).short_title, m.place])
                if self._must_report_resource(m):
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
        if IS_DEV_VERSION:
            for m in self.perception.union(self.memory):
                if m.place is None:
                    warning("%s.model is in memory or perception "
                            "and yet its place is None", m.type_name)

    def direction_to_msg(self, o):
        x, y = self.place_xy
        d = distance(x, y, o.x, o.y)
        if d < self.square_width / 3 / 2:
            return mp.AT_THE_CENTER
        direction = math.degrees(angle(x, y, o.x, o.y, 0))
        mp_direction = direction_to_msgpart(direction)
        if mp_direction == mp.EAST:
            return mp.TO_THE_EAST # special case in French
        if mp_direction == mp.WEST:
            return mp.TO_THE_WEST # special case in French
        return mp.TO_THE + mp_direction

    # immersive mode

    _previous_compass = None

    def say_compass(self):
        compass = direction_to_msgpart(self.o)
        if compass != self._previous_compass:
            voice.item(compass)
            self._previous_compass = compass

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

    def _menu_has_increased(self, type_name, menu):
        for i in _get_relevant_menu(menu):
            if i not in self.previous_menus[type_name]:
                return True
        return False

    def _remember_menu(self, type_name, menu):
        for i in _get_relevant_menu(menu):
            if i not in self.previous_menus[type_name]:
                self.previous_menus[type_name].append(i)

    def _send_menu_alert_if_needed(self, type_name, menu, title):
        if type_name not in self.previous_menus:
            self.previous_menus[type_name] = []
        elif self._menu_has_increased(type_name, menu):
            voice.info(mp.MENU_OF + title + mp.CHANGED)
        self._remember_menu(type_name, menu)

    def send_menu_alerts_if_needed(self):
        if "menu_changed" not in config.verbosity: return
        done = []
        for u in self.player.units:
            u = EntityView(self, u)
            if u.type_name not in done:
                self._send_menu_alert_if_needed(u.type_name, u.strict_menu, u.short_title)
                done.append(u.type_name)

    def summary(self, group, brief=False):
        types = _remove_duplicates(group) # set() would lose the order
        if brief and len(types) > 2:
            return nb2msg(len(group))
        result = []
        for t in types:
            if t == types[-1] and len(types) > 1:
                result += mp.AND
            elif t != types[0]:
                result += mp.COMMA
            result += nb2msg(group.count(t)) + t
        return result

    def place_summary(self, place, me=True, zoom=None, brief=False):
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
            if obj.model.player in self.player.allied and obj.model.player is not self.player:
                allies.append(obj.short_title)
            if obj.model.player is self.player:
                units.append(obj.short_title)
            if getattr(obj.model, "resource_type", None) is not None:
                resources.append(obj.short_title)
        result = []
        if enemies:
            result += mp.COMMA + self.summary(enemies, brief=brief) + mp.ENEMY
        if me and allies:
            result += mp.COMMA + self.summary(allies) + mp.ALLY
        if me and units:
            result += mp.COMMA + self.summary(units)
        if resources and (not enemies or not brief):
            result += mp.COMMA + self.summary(resources)
        return result

    def say_group(self, prefix=[]):
        self.update_group()
        if len(self.group) == 1:
            u = self.dobjets[self.group[0]]
            voice.item(prefix + mp.YOU_CONTROL + u.ext_title + u.orders_txt)
        elif len(self.group) > 1:
            orders = [self.dobjets[x].orders_txt for x in self.group if x in self.dobjets]
            if len(_remove_duplicates(orders)) == 1:
                group = [self.dobjets[x].short_title
                         for x in self.group if x in self.dobjets]
                voice.item(prefix + mp.COMMA + mp.YOU_CONTROL + self.summary(group)
                           + mp.COMMA + orders[0])
            else:
                group = [self.dobjets[x].short_title + mp.COMMA + self.dobjets[x].orders_txt
                         for x in self.group if x in self.dobjets]
                voice.item(prefix + mp.COMMA + mp.YOU_CONTROL + self.summary(group))
        else:
            voice.item(prefix + mp.COMMA + mp.NO_UNIT_CONTROLLED)

    def tell_enemies_in_square(self, place):
        enemies = [x.short_title for x in self.dobjets.values()
                   if x.is_in(place) and self.player.is_an_enemy(x.model)]
        if enemies:
            voice.info(self.summary(enemies, brief=True) + mp.ENEMY + mp.AT + place.title)

    def units_alert(self, units, msg_end, brief=True):
        places = set([x[1] for x in units if x[1] is not None])
        for place in places:
            units_in_place = [x[0] for x in units if x[1] is place]
            s = self.summary(units_in_place, brief=brief)
            if s:
                voice.info(s + msg_end + mp.AT + place.title)
        while units:
            units.pop()

    previous_unit_attacked_alert = None

    previous_scout_info = None

    def scout_info_if_needed(self):
        if "scout_info" not in config.verbosity: return
        if self.scout_info and (self.previous_scout_info is None or
                time.time() > self.previous_scout_info + 10):
            for place in self.scout_info:
                s = self.place_summary(place, me=False, brief=True)
                if s:
                    voice.info(s + mp.AT + place.title)
            self.scout_info = set()
            self.previous_scout_info = time.time()

    previous_units_alert = None

    def units_alert_if_needed(self, place=None):
        if (self.neutralized_units or self.lost_units or self.new_enemy_units) and \
           (self.previous_units_alert is None
                or time.time() > self.previous_units_alert + 10):
            self.units_alert(self.neutralized_units, mp.NEUTRALIZED, brief=False)
            self.units_alert(self.lost_units, mp.LOST)
            self.units_alert(self.new_enemy_units, mp.ENEMY)
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
                titles.insert(-1, mp.AND)
            if titles:
                voice.info(sum(titles, mp.ALERT + mp.AT))
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
        if order in ("default", "join_group"):
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
            voice.item(mp.NO_UNIT_CONTROLLED)
        elif self.order is None: # nothing to validate
            self.cmd_command_unit()
        elif self.an_order_not_requiring_a_target_is_selected:
            self.send_order(self.order.encode, None, args)
            voice.item(self.order.title) # confirmation
            self._previous_order = self.order
        elif self.an_order_requiring_a_target_is_selected:
            if self.order not in self.orders():
                # the order is not in the menu anymore
                psounds.play_stereo(sounds.get_sound(BEEP_SOUND))
            elif self.ui_target.id is not None:
                self.send_order(self.order.encode, self.ui_target.id, args)
                # confirmation
                voice.item(self.order.title + self.ui_target.title)
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
                u = self.dobjets[u]
                order = u.model.get_default_order(self.ui_target.id)
                if order is not None:
                    msg = OrderTypeView(order, u).title + self.ui_target.title
                    if msg not in msgs:
                        msgs.append(msg)
        confirmation = []
        for msg in msgs:
            confirmation += msg + mp.COMMA
        if confirmation:
            voice.item(confirmation)
        else:
            voice.item(mp.BEEP)

    def cmd_default(self, *args):
        if not self.group:
            voice.item(mp.NO_UNIT_CONTROLLED)
        elif self.ui_target.id is not None:
            self.send_order("default", self.ui_target.id, args)
            self._say_default_confirmation()
        self.order = None

    def cmd_unit_status(self):
        try:
            place = self.dobjets[self.group[0]].place.title
        except:
            place = self.place.title
        self.say_group(place)
        if self.group:
            self.follow_mode = True
            self._follow_if_needed()

    def cmd_help(self, incr):
        incr = int(incr)
        voice.item(help_msg("game", incr))

    def _minimap_stereo(self, place):
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
            voice.item(unit.ext_title + unit.orders_txt + mp.AWAITING_YOUR_ORDERS)
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
        if keyboard_types and not types: # no keyboard type actually exists in the style
            types = [None] # will select nothing
        return types, local, idle, even_if_no_menu

    def cmd_select_unit(self, inc, *args):
        inc = int(inc)
        self._select_unit(inc, *self._arrange(args))

    def cmd_select_units(self, *args):
        self._select_unit(1, *(list(self._arrange(args)) + [True]))
        self._regroup(1, *self._arrange(args))

    # recallable groups

    def cmd_set_group(self, name, *args):
        self.send_order("reset_group", name, args)
        self.send_order("join_group", name, args)

    def cmd_append_group(self, name, *args):
        self.send_order("join_group", name, args)

    def cmd_recall_group(self, name, *args):
        if name in self.player.groups:
            self.group = [u.id for u in self.player.groups[name]]
        else:
            self.group = []
        self.say_group()

    # select order

    order = None

    def orders(self, inactive_only=False, inactive_included=False):
        if inactive_included:
            menu_type = "menu"
            ok = lambda o, u: True
        elif inactive_only:
            menu_type = "menu"
            ok = lambda o, u: o not in u.strict_menu
        else:
            menu_type = "strict_menu"
            ok = lambda o, u: True
        menu = []
        done = []
        for u in self.group:
            if u in self.dobjets:
                u = self.dobjets[u]
                for o in getattr(u, menu_type):
                    if o not in done and ok(o, u):
                        menu.append(OrderTypeView(o, u))
                        done.append(o)
        # sort the menu by index
        menu.sort(key=lambda x: x.index)
        return menu

    @property
    def an_order_not_requiring_a_target_is_selected(self):
        return self.order and self.order.nb_args == 0

    @property
    def an_order_requiring_a_target_is_selected(self):
        return self.order and self.order.nb_args

    def _select_order(self, order, help=True):
        self.order = order
        # say the new current order
        msg = self.order.title + mp.COMMA + self.order.full_comment
        if help:
            if self.order.nb_args == 0:
                msg += mp.COMMA + mp.CONFIRM
            else:
                msg += mp.COMMA + mp.SELECT_TARGET_AND_CONFIRM
        voice.item(msg)

    def cmd_select_order(self, inc, *args):
        inc = int(inc)
        # call self.orders() once (can take a long time)
        orders = self.orders(inactive_only="inactive_only" in args,
                             inactive_included="inactive_included" in args)
        # if no menu then do nothing
        if not orders:
            voice.item(mp.NOTHING)
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
        self._select_order(orders[index], help="inactive_only" not in args)

    def cmd_order_shortcut(self):
        if self.group:
            msg = []
            for o in self.orders():
                shortcut = o.shortcut
                if shortcut:
                    msg += [str(shortcut)] + o.title + mp.COMMA
            if msg:
                self.shortcut_mode = True
                voice.item(msg)
                return
        voice.item(mp.BEEP)

    def cmd_do_again(self, *args):
        if self._previous_order is not None and self.group:
            self._select_order(self._previous_order)
            if "now" in args and self.order.nb_args == 0:
                args = [a for a in args if a in ("queue_order", "imperative")]
                self.cmd_validate(*args)

    # select square

    @property
    def place_xy(self):
        return self.place.x / 1000.0, self.place.y / 1000.0

    @property
    def xcmax(self):
        return self.world.nb_columns - 1

    @property
    def ycmax(self):
        return self.world.nb_lines - 1

    def coords_in_map(self, square):
        if square is not None:
            return square.col, square.row
        return -1, -1

    def move_to_square(self, square):
        if self.place is not square and self.coords_in_map(square) != (-1, -1):
            self.place = square
            self._silence_square()
            self.display()

    def _silence_square(self):
        for o in self.dobjets.values():
            if not o.is_in(self.place):
                o.stop()
        sound_stop(stop_voice_too=False) # cut the long nonlooping environment sounds

    def _square_terrain(self, place):
        result = []
        t = place.type_name
        if t:
            title = style.get(t, "title")
            if title:
                result += mp.COMMA + title
        if place.high_ground: result += mp.COMMA + mp.PLATEAU
        return result
        
    def square_postfix(self, place):
        postfix = []
        if place in self.scouted_squares:
            postfix += self._square_terrain(place)
        elif place in self.scouted_before_squares:
            postfix += self._square_terrain(place)
            postfix += mp.COMMA + mp.IN_THE_FOG
        else:
            postfix += mp.COMMA + mp.UNKNOWN
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
        return self.world.grid[(xc, yc)]

    def _get_prefix_and_collision(self, new_square, dxc, dyc):
        if new_square is self.place:
            return style.get("parameters", "no_path_in_this_direction"), True
        if self.place not in self.scouted_before_squares or \
           self.place.is_water and new_square.is_water:
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
        no_collision = "no_collision" in args
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
            if int(math.copysign(dxc + dyc, 1)) > 1: # several squares at a time
                # assertion: dxc == 0 or dyc == 0
                if dxc:
                    step = int(math.copysign(1, dxc)), 0
                else:
                    step = 0, int(math.copysign(1, dyc))
                prefixes = []
                for _ in range(int(math.copysign(dxc + dyc, 1))):
                    new_square = self._compute_move(*step)
                    prefix, collision = self._get_prefix_and_collision(new_square, *step)
                    if not no_collision:
                        prefixes += prefix
                    if not collision or no_collision:
                        self.move_to_square(new_square)
                    else:
                        break
                self._select_and_say_square(self.place, prefixes)
            elif no_collision: # one square at a time without collision
                new_square = self._compute_move(dxc, dyc)
                self.move_to_square(new_square)
                self._select_and_say_square(self.place)
            else: # one square at a time with collision
                new_square = self._compute_move(dxc, dyc)
                prefix, collision = self._get_prefix_and_collision(new_square, dxc, dyc)
                if not collision:
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
            voice.item(mp.NOTHING)

    def cmd_select_scouted_square(self, increment):
        self._select_square_from_list(increment, self.scouted_squares)

    def cmd_select_conflict_square(self, increment):
        enemy_units = [o for o in self.dobjets.values()
                       if o.player and o.player.player_is_an_enemy(self.player)]
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
            if self.place not in self.scouted_squares:
                self.y -= self.square_width # lower sounds if fog of war
        psounds.update()

    def cmd_toggle_zoom(self):
        if not self.place:
            return
        self.zoom_mode = not self.zoom_mode
        if self.zoom_mode:
            self.zoom = Zoom(self)
            self.target = None
            self.zoom.say(prefix=mp.ZOOM+mp.IS_NOW_ON+mp.COMMA)
        else:
            self._select_and_say_square(self.place, prefix=mp.ZOOM+mp.IS_NOW_OFF+mp.COMMA)

    # display

    def display_metrics(self):
        warn = (255, 0, 0)
        normal = (0, 200, 0)
        screen_render("total delay: %sms" % chrono.ms(time.time() - self.next_update),
                      (0, 30),
                      color=warn if time.time() > self.next_update else normal)
        if hasattr(self.server, "turn"):
            screen_render("com turn(sim subturn): %s(%s/%s)" % (self.server.turn, self.server.sub_turn + 1, self.server.fpct),
                      (0, 45))
            screen_render("com delay: %sms" % chrono.ms(self.server.delay),
                      (0, 60),
                      color=warn if self.server.delay > 0 else normal)
        screen_render(chrono.text("ping"), (-1, 0), right=True)
        screen_render(chrono.text("update", label="world update"), (-1, 30), right=True)
        screen_render(chrono.text("animate"), (-1, 45), right=True)
        screen_render(chrono.text("display"), (-1, 60), right=True)
        screen_render("speed: %.0f sim turns per second (normal x%.1f)"
                      % (self._get_tps(), self._get_relative_speed()),
                      (0, 15),
                      color=warn if self._get_relative_speed() < self.speed * .9
                      else normal)

    _must_display_target_info = False

    def _display_target_info(self):
        dy = 0
        if self.target is not None:
            screen_render("TARGET INFO", (-1, 100 + dy), right=True)
            dy += 15
            try:
                screen_render(repr(self.target.model), (-1, 100 + dy), color=(255, 255, 255), right=True)
                dy += 15
                d = self.target.model.__dict__
                for k in sorted(d):
                    screen_render(k + ": " + repr(d[k]), (-1, 100 + dy), right=True)
                    dy += 15
            except:
                exception("error inspecting target: %s", self.target)
        if self.place is not None:
            dy += 15
            screen_render("PLACE INFO", (-1, 100 + dy), right=True)
            dy += 15
            try:
                screen_render(repr(self.place), (-1, 100 + dy), color=(255, 255, 255), right=True)
                dy += 15
                d = self.place.__dict__
                for k in sorted(d):
                    screen_render(k + ": " + repr(d[k]), (-1, 100 + dy), right=True)
                    dy += 15
            except:
                exception("error inspecting place: %s", self.place)
        dy = 0
        screen_render("PLAYER INFO", (-1, 100 + dy))
        dy += 15
        d = self.player.__dict__
        for k in sorted(d):
            try:
                screen_render(k + ": " + repr(d[k]), (-1, 100 + dy))
                dy += 15
            except:
                exception("error inspecting player: %s", self.player)

    def display(self):
        if get_screen() is None:
            return # this might allow some machines to work without any display
        chrono.start("display")
        get_screen().fill((0, 0, 0))
        if get_fullscreen():
            self.grid_view.display()
            if self.mouse_select_origin and self.mouse_select_origin != pygame.mouse.get_pos():
                x, y = self.mouse_select_origin
                x2, y2 = pygame.mouse.get_pos()
                pygame.draw.rect(get_screen(), (255, 255, 255), (min(x, x2), min(y, y2), abs(x - x2), abs(y - y2)), 1)
        elif not IS_DEV_VERSION:
            screen_render(
                "[Ctrl + F2] display",
                pygame.display.get_surface().get_rect().center,
                center=True
            )
        if self._must_play_tick or IS_DEV_VERSION:
            self.display_metrics()
        if self._must_display_target_info and get_fullscreen():
            self._display_target_info()
        screen_render_subtitle()
        pygame.display.flip()
        chrono.stop("display")

    def cmd_fullscreen(self):
        toggle_fullscreen()

    # resources

    @property
    def resources(self):
        return [int(x / PRECISION) for x in self.player.resources]

    @property
    def available_food(self):
        return self.player.available_food

    @property
    def used_food(self):
        return self.player.used_food

    def cmd_resource_status(self, resource_type):
        resource_type = int(resource_type)
        try:
            voice.item(nb2msg(self.resources[resource_type]) + style.get(
                "parameters", "resource_%s_title" % resource_type))
        except IndexError:
            voice.item(mp.BEEP)

    def cmd_food_status(self):
        voice.item(nb2msg_f(self.available_food)
                   + style.get("parameters", "food_title")
                   + mp.TO + nb2msg(self.used_food))

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
                if "resources" in config.verbosity and must_be_said(r):
                    self.send_msg_if_playing(nb2msg(r) + style.get(
                        "parameters", "resource_%s_title" % i),
                        update_type="resource_%s" % i)
        if self.available_food != self._previous_available_food or \
           self.used_food > self._previous_used_food or \
           (self.used_food < self._previous_used_food and
            self._previous_used_food == self.available_food):
            if "food" in config.verbosity and \
               0 <= self.available_food - self.used_food <= \
               self.available_food * .20:
                self.send_msg_if_playing(
                    nb2msg_f(self.available_food)
                    + style.get("parameters", "food_title")
                    + mp.TO + nb2msg(self.used_food),
                    update_type="food")
            self._previous_available_food = self.available_food
            self._previous_used_food = self.used_food
