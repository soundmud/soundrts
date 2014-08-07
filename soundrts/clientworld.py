import random
import time

import pygame

from clientmedia import *
from constants import *
from definitions import *
from msgs import nb2msg
from worldunit import *


##color_table = {81: "gold", 80: "forestgreen", 82: "white", 83: "hotpink",
##                  84: "dimgray", 99: "violetred", 122: "yellowgreen", 153: "blue",
##                  85: "brown", 86: "red", 87:"darkorange"}
##warning("uh")
##for k, v in color_table.items():
##    color_table[k] = pygame.Color(v)
##warning("uh oh")
# precalculated dictionnary (crashes with pygame 1.8.1)
color_table = {99: (208, 32, 144, 255), 80: (34, 139, 34, 255), 81: (255, 215, 0, 255), 82: (255, 255, 255, 255), 83: (255, 105, 180, 255), 84: (105, 105, 105, 255), 85: (165, 42, 42, 255), 86: (255, 0, 0, 255), 87: (255, 140, 0, 255), 153: (0, 0, 255, 255), 122: (154, 205, 50, 255)}
R = int(0.5 * 10)
R2 = R * R

def compute_title(type_name):
    t = style.get(type_name, "title")
    if t is None:
        return []
    else:
        return [int(x) for x in t]

def substitute_args(t, args):
    if t is not None:
        while "$1" in t:
            i = t.index("$1")
            del t[i]
            t[i:i] = args[0]
        return t

def must_be_said(nb):
    if nb <= 10:
        return True
    elif nb <= 100:
        return nb % 10 == 0
    else:
        return nb % 100 == 0


class Objet(object):

    next_step = None

    loop_noise = None
    loop_volume = 0
    loop_source = None

    repeat_noises = []
    repeat_interval = -1
    repeat_source = None
    next_repeat = None
    
    def __init__(self, interface, model):
        self.interface = interface
        self.model = model
        self.footstep_interval = .5 + random.random() * .2 # to avoid strange synchronicity of footsteps when several units are walking

    def __getattr__(self, name):
        v = getattr(self.model, name)
        if name in ["x", "y"]:
            v /= 1000.0
        elif name in ("qty", "hp", "hp_max", "mana", "mana_max"):
            v = int(v / PRECISION)
        return v

    def __getstate__(self):
        odict = self.__dict__.copy() # copy the dict since we change it
        for k in ("loop_source", "repeat_source"):
            if odict.has_key(k):
                del odict[k] # remove Sound entry
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)   # update attributes
        self.loop_source = None
        self.repeat_source = None

    @property
    def ext_title(self):
        try:
            return self.title + [107] + self.place.title
        except:
            exception("problem with %s.ext_title", self.type_name)

    def _menu(self, strict=False):
        menu = []
        try: # XXX remove this "try... except" when rules.txt checking is implemented
            for order_class in _orders_list:
                menu.extend(order_class.menu(self, strict=strict))
        except:
            exception("problem with %s.menu() of %s", order_class, self.type_name)
        return menu

    @property
    def menu(self):
        return self._menu()

    @property
    def strict_menu(self):
        return self._menu(strict=True)

    @property
    def orders_txt(self):
        t = []
        prev = None
        nb = 0
        for o in self.orders:
            if prev:
                if o.keyword == "train" and prev.type == o.type:
                    nb += 1
                else:
                    t += OrderView(prev, self.interface).title_msg(nb)
                    if o.keyword == "train":
                        prev = o
                        nb = 1
                    else:
                        t += OrderView(o, self.interface).title_msg()
                        prev = None
            elif o.keyword == "train":
                prev = o
                nb = 1
            else:
                t += OrderView(o, self.interface).title_msg()
        if prev:
            t += OrderView(prev, self.interface).title_msg(nb)
        return t

    @property
    def title(self):
        if isinstance(self.model, BuildingSite):
            title = compute_title(self.type.type_name) + compute_title(BuildingSite.type_name)
        else:
            title = self.short_title[:]
        if self.player:
            if self.player == self.interface.player:
                title += nb2msg(self.number)
            elif self.player in self.interface.player.allied:
                title += [4286] + nb2msg(self.player.number) + [self.player.client.login] # "allied 2"
            elif hasattr(self.player, "number") and self.player.number:
                title += [88] + nb2msg(self.player.number) + [self.player.client.login] # "ennemy 2"
            else: # "npc_ai"
                title += [88] # enemy
        return title

    @property
    def short_title(self):
        return compute_title(self.type_name)

    @property
    def hp_status(self):
        return nb2msg(self.hp) + [39] + nb2msg(self.hp_max)

    @property
    def mana_status(self):
        if self.mana_max > 0:
            return nb2msg(self.mana) + [4247] + nb2msg(self.mana_max)
        else:
            return []

    @property
    def upgrades_status(self):
        result = []
        for u in self.upgrades:
            result += style.get(u, "title")
        return result

    @property
    def description(self):
        d = []
        try:
            if hasattr(self, "qty") and self.qty:
                d += [134] + nb2msg(self.qty) + style.get("parameters", "resource_%s_title" % self.resource_type)
            if hasattr(self, "hp"):
                d += self.hp_status
            if hasattr(self, "mana"):
                d += self.mana_status
            if hasattr(self, "upgrades"):
                d += self.upgrades_status
            if hasattr(self, "is_invisible_or_cloaked") and \
               self.is_invisible_or_cloaked():
                d += [9998, 4289]
            if getattr(self, "is_a_detector", 0):
                d += [9998, 4290]
            if getattr(self, "is_a_cloaker", 0):
                d += [9998, 4291]
        except:
            pass # a warning is given by style.get()
        return d

    def is_a_useful_target(self):
        # (useful for a worker)
        # resource deposits, building lands, damaged repairable units or buildings
        return self.qty > 0 or \
               self.is_a_building_land or \
               self.is_repairable and self.hp < self.hp_max

    def color(self):
        if self.short_title and self.short_title[0] in color_table.keys():
            return color_table[self.short_title[0]]
#            return (255, 255, 255)
#            return pygame.color.Color("red")
#            return pygame.color.Color(self.color_table[self.short_title[0]])
        else:
            try:
                return (255, (int(self.short_title[0]) * int(self.short_title[0])) % 256, int(self.short_title[0]) % 256)
            except:
                return (255, 255, 255)

    def corrected_color(self):
        if self.model in self.interface.memory:
            return tuple([x / 2 for x in self.color()])
        else:
            return self.color()

    def footstepnoise(self):
        # assert: "only immobile objects must be taken into account"
        result = style.get(self.type_name, "move")
        if self.airground_type == "ground":
            d_min = 9999999
            for m in self.place.objects:
                if getattr(m, "speed", 0):
                    continue
                g = style.get(m.type_name, "ground")
                if g and style.has(self.type_name, "move_on_%s" % g[0]):
                    try:
                        k = float(g[1])
                    except IndexError:
                        k = 1.0
                    try:
                        o = self.interface.dobjets[m.id]
                    except KeyError: # probably caused by the world client updates
                        continue
                    d = distance(o.x, o.y, self.x, self.y) / k
                    if d < d_min:
                        result = style.get(self.type_name, "move_on_%s" % g[0])
                        d_min = d
        return result

    def footstep(self):
        if self.is_moving:
            if self.next_step is None:
                self.step_side = 1
                self.next_step = time.time() + random.random() * self.footstep_interval # start at different moments
            elif time.time() > self.next_step:
                if self.interface.immersion and (self.x, self.y) == (self.interface.x, self.interface.y):
                    v = 1 / 2.0
                else:
                    v = 1
                try:
                    self.launch_event(self.footstepnoise()[self.step_side], v, priority=-10, limit=FOOTSTEP_LIMIT)
                except IndexError:
                    pass
                self.next_step = time.time() + self.footstep_interval / self.interface.speed
                self.step_side = 1 - self.step_side
        else:
            self.next_step = None

    def get_style(self, attr):
        st = style.get(self.type_name, attr)
        if st and st[0] == "if_me":
            if self.player in self.interface.player.allied:
                try:
                    return st[1:st.index("else")]
                except ValueError:
                    return st[1:]
            else:
                try:
                    return st[st.index("else") + 1:]
                except ValueError:
                    return []
        return st

    def _get_noise_style(self):
        if self.activity:
            st = self.get_style("noise_when_%s" % self.activity)
            if st:
                return st
        if hasattr(self, "hp"):
            if self.hp < self.hp_max * 2 / 3:
                st = self.get_style("noise_if_damaged")
                if st:
                    return st
            if self.hp < self.hp_max / 3:
                st = self.get_style("noise_if_very_damaged")
                if st:
                    return st
        return self.get_style("noise")

    def _set_noise(self, st):
        self.repeat_noises = []
        self.repeat_interval = -1
        self.loop_noise = None
        self.loop_volume = 0
        self.ambient_noise = False
        if not st:
            return
        if st[0] == "ambient":
            self.ambient_noise = True
            del st[0]
        if st[0] == "loop":
            self.loop_noise = st[1]
            try:
                self.loop_volume = float(st[2])
            except IndexError:
                self.loop_volume = 1
        elif st[0] == "repeat":
            self.repeat_interval = float(st[1])
            self.repeat_noises = st[2:]

    def update_noise(self):
        st = self._get_noise_style()
        self._set_noise(st)

    def launch_event_style(self, attr, alert=False, priority=0):
        st = self.get_style(attr)
        if not st:
            return
        s = random.choice(st)
        if alert and self.place is not self.interface.place:
            self.launch_alert(s)
        else:
            self.launch_event(s, priority=priority)

    def on_use_complete(self, ability):
        st = style.get(ability, "alert")
        if not st:
            return
        s = random.choice(st)
        self.launch_alert(s)

    def _loop_noise(self):
        if self.loop_noise is not None:
            if self.loop_source is None:
                # same priority level as "footstep", to avoid unpleasant interruptions
                self.loop_source = psounds.play_loop(self.loop_noise, self.loop_volume, self.x, self.y, -10)
            else :
                self.loop_source.move(self.x, self.y)
        else:
            self.stop()

    def _repeat_noise(self):
        if self.repeat_noises:
            if self.next_repeat is None:
                self.next_repeat = time.time() + random.random() * self.repeat_interval # to start at different moments
            # don't start a new "repeat sound" if the previous "repeat sound" hasn't stopped yet
            elif time.time() > self.next_repeat and getattr(self.repeat_source, "has_stopped", True):
                self.repeat_source = self.launch_event(random.choice(self.repeat_noises), priority=-20, ambient=self.ambient_noise)
                self.next_repeat = time.time() + self.repeat_interval * (.8 + random.random() * .4)
                if time.time() > self.next_repeat:
                    self.next_repeat = None
        else:
            self.next_repeat = None

    def animate(self):
        if self.place is self.interface.place:
            self.footstep()
            self.update_noise()
            self._loop_noise()
            self._repeat_noise()
            self.render_hp()

    def stop(self): # arreter les sons en boucle
        if self.loop_source is not None:
            self.loop_source.stop()
            self.loop_source = None

    previous_hp = None

    def _hp_noise(self, hp):
        return int(hp * 10 / self.hp_max)

    def render_hp_evolution(self):
        if self.previous_hp is not None:
            if (self.hp < self.previous_hp # always noise if less HP
                or self._hp_noise(self.hp) != self._hp_noise(self.previous_hp)):
                self.launch_event_style("proportion_%s" % self._hp_noise(self.hp))
            if self.hp > self.previous_hp and self.is_healable:
                self.launch_event_style("healed")

    def render_hp(self):
        if hasattr(self, "hp"):
            if self.hp < 0: return # TODO: remove this line (isolate the UI or use a deep copy of perception)
            if self.hp != self.previous_hp:
                self.render_hp_evolution()
                self.previous_hp = self.hp

    def notify(self, event_and_args):
        e_a = event_and_args.split(",")
        event = e_a[0]
        args = e_a[1:]
        if hasattr(self, "on_" + event):
            getattr(self, "on_" + event)(*args)
        else:
            self.launch_event_style(event)

    def on_collision(self):
        self.launch_event_style("blocked") # "blocked" is more precise than "collision"

    def on_attack(self):
        self.launch_event_style("attack", alert=True)

    def on_flee(self):
        self.launch_event_style("flee", alert=True)

    def on_store(self, resource_type):
        self.launch_event_style("store_resource_%s" % resource_type)

    def on_order_ok(self):
        if self.player is not self.interface.player: return
        self.launch_event_style("order_ok", alert=True)

    def on_order_impossible(self, reason=None):
        if self.player is not self.interface.player: return
        self.launch_event_style("order_impossible", alert=True)
        if reason is not None:
            voice.info(style.get("messages", reason))

    def on_production_deferred(self):
        voice.info(style.get("messages", "production_deferred"))

    def on_win_fight(self):
        self.launch_event_style("win_fight", alert=True)
        self.interface.units_alert_if_needed()

    def on_lose_fight(self):
        self.launch_event_style("lose_fight", alert=True)
        self.interface.units_alert_if_needed(place=self.place)

    def launch_event(self, sound, volume=1, priority=0, limit=0, ambient=False):
        if self.place is self.interface.place:
            return psounds.play(sound, volume, self.x, self.y, priority, limit, ambient)

    def launch_alert(self, sound):
        self.interface.launch_alert(self.place, sound)

    def on_death_by(self, attacker_id):
        attacker = self.interface.dobjets.get(attacker_id)
        if self.player is self.interface.player:
            self.interface.lost_units.append([self.short_title, self.place])
        if getattr(attacker, "player", None) is self.interface.player:
            self.interface.neutralized_units.append([self.short_title, self.place]) # TODO: "de " self.player.name
        friends = [u for u in self.player.units if u.place is self.place and u.id != self.id]
        friend_soldiers = [u for u in friends if u.menace]
        # two cases requires an alert:
        # - the last soldier died (no more protection)
        # - the last "non soldier" unit died (no more unit at all)
        if not friend_soldiers and self.menace or not friends:
            if self.player == self.interface.player:
                self.on_lose_fight()
            if getattr(attacker, "player", None) == self.interface.player:
                attacker.on_win_fight()

    def unit_attacked_alert(self):
        self.interface.alert_squares[self.place] = time.time()
        self.interface.squares_alert_if_needed()
        if self.interface.previous_unit_attacked_alert is None or \
           time.time() > self.interface.previous_unit_attacked_alert + 10:
            self.launch_event_style("alert", alert=True)
            self.interface.previous_unit_attacked_alert = time.time()

    def on_wounded(self, attacker_type, attacker_id, level):
        if self.player == self.interface.player:
            self.unit_attacked_alert()
        s = style.get(attacker_type, "attack_hit_level_%s" % level)
        if s is not None:
            if s:
                self.launch_event(random.choice(s))
        else:
            warning("no sound found for: %s %s", attacker_type, "attack_hit_level_%s" % level)
        if get_fullscreen() and attacker_id in self.interface.dobjets:
            a = self.interface.dobjets[attacker_id]
            self.interface.grid_view._update_coefs()
            if self.interface.player.is_an_enemy(a):
                color = (255, 0, 0)
            else:
                color = (0, 255, 0)
            pygame.draw.line(get_screen(), color,
                             self.interface.grid_view.object_coords(self),
                             self.interface.grid_view.object_coords(a))
            pygame.draw.circle(get_screen(), (100, 100, 100),
                               self.interface.grid_view.object_coords(self), R*3/2, 0)
            pygame.display.flip() # not very clean but seems to work (persistence of vision?)
            # better: interface.anims queue to render when the time has come
            # (not during the world model update)

    def on_enter_square(self):
        pass

    def on_exhausted(self):
        self.launch_event_style("exhausted")
        voice.info(self.title + [144])

    def on_completeness(self, s): # building train or upgrade
        self.launch_event_style("production")
        self.launch_event_style("proportion_%s" % s)

    def on_complete(self):
        if self.player is not self.interface.player: return
        self.launch_event_style("complete", alert=True)
        if must_be_said(self.number):
            voice.info(substitute_args(self.get_style("complete_msg"), [self.title]))
        self.interface.send_menu_alerts_if_needed() # not necessary for "on_repair_complete" (if it existed)

    def on_research_complete(self):
        voice.info(self.get_style("research_complete_msg"))
        self.interface.send_menu_alerts_if_needed()

    def on_added(self):
        self.launch_event_style("added", alert=True)
        if must_be_said(self.number):
            voice.info(substitute_args(self.get_style("added_msg"), [self.ext_title]))


class GridView(object):

    def __init__(self, interface):
        self.interface = interface

    def _display(self):
        # backgrounds
        for xc in range(0, self.interface.xcmax + 1):
            for yc in range(0, self.interface.ycmax + 1):
                sq = self.interface.server.player.world.grid[(xc, yc)]
                x, y = xc * self.square_view_width, self.ymax - yc * self.square_view_height
                if sq in self.interface.server.player.detected_squares:
                    color = (0, 25, 25)
                elif sq in self.interface.server.player.observed_squares:
                    color = (0, 25, 0)
                elif sq in self.interface.server.player.observed_before_squares:
                    color = (15, 15, 15)
                else:
                    color = (0, 0, 0)
                    continue
                if sq.high_ground:
                    color = (color[0]*2, color[1]*2, color[2]*2)
                draw_rect(color, x, y - self.square_view_height, self.square_view_width, self.square_view_height, 0)
        # grid
        color = (100, 100, 100)
        for x in range(0, self.interface.xcmax + 2):
            draw_line(color, (x * self.square_view_width, 0), (x * self.square_view_width, (self.interface.ycmax + 1)* self.square_view_height))
        for y in range(0, self.interface.ycmax + 2):
            draw_line(color, (0, y * self.square_view_height), ((self.interface.xcmax + 1) * self.square_view_width, y * self.square_view_height))

    def active_square_view_display(self):
        xc, yc = self.interface.coords_in_map(self.interface.place)
        x, y = xc * self.square_view_width, self.ymax - yc * self.square_view_height
        if self.interface.target is None:
            color = (255, 255, 255)
        else:
            color = (150, 150, 150)
        draw_rect(color, x, y - self.square_view_height, self.square_view_width, self.square_view_height, 1)

    def object_coords(self, o):
        x = int(o.x / self.interface.square_width * self.square_view_width)
        y = int(self.ymax - o.y / self.interface.square_width * self.square_view_height)
        return (x, y)

    def display_object(self, o):
        if getattr(o, "is_inside", False):
            return
        if self.interface.target is not None and self.interface.target is o:
            width = 0 # fill circle
        else:
            width = 1
        x, y = self.object_coords(o)
        if isinstance(o.model, (Building, BuildingSite)):
            draw_rect(o.corrected_color(), x-R, y-R, R*2, R*2, width)
        else:
            pygame.draw.circle(get_screen(), o.corrected_color(), (x, y), R, width)
        if getattr(o.model, "player", None) is not None:
            if o.id in self.interface.group:
                color = (0,255,0)
            elif o.player is self.interface.player:
                color = (0,55,0)
            elif o.player in self.interface.player.allied:
                color = (0,0,155)
            elif o.player.is_an_enemy(self.interface.player):
                color = (155,0,0)
            else:
                color = (0, 0, 0)
            pygame.draw.circle(get_screen(), color, (x, y), R/2, 0)
            if getattr(o, "hp", None) is not None and \
               o.hp != o.hp_max:
                hp_prop = 100 * o.hp / o.hp_max
                if hp_prop > 80:
                    color = (0, 255, 0)
##                elif hp_prop > 50:
##                    color = (0, 255, 0)
                else:
                    color = (255, 0, 0)
                W = R - 2
                if color != (0, 255, 0):
                    pygame.draw.line(get_screen(), (0, 55, 0),
                                 (x - W, y - R - 2),
                                 (x - W + 2 * W, y - R - 2))
                pygame.draw.line(get_screen(), color,
                                 (x - W, y - R - 2),
                                 (x - W + hp_prop * (2 * W) / 100, y - R - 2))

    def display_objects(self):
        for o in self.interface.dobjets.values():
            self.display_object(o)
            if o.place is None and not o.is_inside \
               and not (self.interface.already_asked_to_quit or
                        self.interface.end_loop):
                warning("%s.place is None", o.type_name)
                if o.is_memory:
                    warning("(memory)")

    def _update_coefs(self):
        self.square_view_width = self.square_view_height = min((get_screen().get_width() - 200) / (self.interface.xcmax + 1),
            get_screen().get_height() / (self.interface.ycmax + 1)) # 200 = graphic console
        self.ymax = self.square_view_height * (self.interface.ycmax + 1)

    def _collision_display(self):
        for t, c in (("ground", (0, 0, 255)), ("air", (255, 0, 0))):
            for ox, oy in self.interface.collision_debug[t].xy_set():
                ox /= 1000.0
                oy /= 1000.0
                x = int(ox / self.interface.square_width * self.square_view_width)
                y = int(self.ymax - oy / self.interface.square_width * self.square_view_height)
                pygame.draw.circle(get_screen(), c, (x, y), 0, 0)

    def display(self):
        self._update_coefs()
        self._display()
        self.display_objects()
        self.active_square_view_display()
        if self.interface.collision_debug:
            self._collision_display()

    def square_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        xc = x / self.square_view_width
        yc = (self.ymax - y) / self.square_view_height
        if 0 <= xc <= self.interface.xcmax and 0 <= yc <= self.interface.ycmax:
            return self.interface.server.player.world.grid[(xc, yc)]

    def object_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        for o in self.interface.dobjets.values():
            xo, yo = self.object_coords(o)
            if square_of_distance(x, y, xo, yo) <= R2 + 1: # XXX + 1 ?
                return o

    def units_from_mouserect(self, pos, pos2):
        result= []
        self._update_coefs()
        x, y = pos
        x2, y2 = pos2
        if x > x2: x, x2 = x2, x
        if y > y2: y, y2 = y2, y
        for o in self.interface.units():
            xo, yo = self.object_coords(o)
            if x < xo < x2 and y < yo < y2:
                result.append(o.id)
        return result


def order_comment(order, unit):
    return create_order(order, unit).full_comment

def order_args(order, unit):
    return create_order(order, unit).nb_args

def order_shortcut(order, unit):
    return create_order(order, unit).get_shortcut()

def create_order(order, unit):
    """Create Order instance from string."""
    o = order.split()
    return OrderView(ORDERS_DICT[o[0]](unit, o[1:]))


class OrderView(object):

    comment = []
    title = []
    index = None
    shortcut = None

    def __init__(self, model, interface=None):
        self.model = model
        self.interface = interface
        for k, v in style.get_dict(model.keyword).items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                warning("in %s: %s doesn't have any attribute called '%s'", model.keyword, self.__class__.__name__, k)

    def __getattr__(self, name):
        return getattr(self.model, name)

    @property
    def requirements_msg(self):
        and_index = 0
        msg = []
        for t in self.missing_requirements:
            and_index = len(msg)
            msg += style.get(t, "title")
        if not self.missing_requirements:
            for i, c in enumerate(self.cost):
                if c:
                    and_index = len(msg)
                    msg += nb2msg(c / PRECISION) + style.get("parameters", "resource_%s_title" % i)
            if self.food_cost:
                and_index = len(msg)
                msg += nb2msg(self.food_cost, genre="f") + style.get("parameters", "food_title")
        # add "and" if there are at least 2 requirements
        if and_index > 0:
            msg[and_index:and_index] = style.get("parameters", "and")
        if msg:
            msg[0:0] = style.get("parameters", "requires")
        return msg

    @property
    def full_comment(self):
        return self.comment + self.requirements_msg

    def title_msg(self, nb=1):
        if self.is_deferred:
            result = style.get("messages", "production_deferred")
        else:
            result = []
        result += self.title
        if self.type is not None:
            t = style.get(self.type.type_name, "title")
            if nb != 1:
                t = nb2msg(nb) + t
            result = substitute_args(result, [t])
        if self.target is not None:
            if self.keyword == "build_phase_two":
                result += style.get(self.target.type.type_name, "title")
            else:
                result += Objet(self.interface, self.target).title
        return result

    def get_shortcut(self):
        if self.shortcut:
            return unicode(self.shortcut[0])
        if self.type and self.type.type_name:
            s = style.get(self.type.type_name, "shortcut", False)
            if s:
                return unicode(s[0])


def order_title(order):
    o = order.split()
    t = style.get(o[0], "title")
    if t is None:
        t = []
        warning("%s.title is None", o[0])
    if len(o) > 1:
        t2 = style.get(o[1], "title")
        if t2 is None:
            warning("%s.title is None", o[1])
        else:
            t = substitute_args(t, [t2])
    return t

def order_index(x):
    return _ord_index(x.split()[0])

def _ord_index(keyword):
    try:
        return float(style.get(keyword, "index")[0])
    except:
        warning("%s.index should be a number (check style.txt)", keyword)
        return 9999 # end of the list

def _has_ord_index(keyword):
    return style.has(keyword, "index")

_orders_list = ()

def update_orders_list():
    global _orders_list
    # this sorted list of order classes is used when generating the menu
    _orders_list = sorted([_x for _x in ORDERS_DICT.values()
                          if _has_ord_index(_x.keyword)],
                         key=lambda x:_ord_index(x.keyword))
