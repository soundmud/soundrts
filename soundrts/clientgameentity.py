import random
import time

from clientgamenews import must_be_said
from clientmedia import voice, distance, psounds, get_fullscreen
from constants import FOOTSTEP_LIMIT  
from definitions import style
from lib.log import warning, exception
from msgs import nb2msg
from nofloat import PRECISION
from worldunit import BuildingSite


##color_table = {81: "gold", 80: "forestgreen", 82: "white", 83: "hotpink",
##                  84: "dimgray", 99: "violetred", 122: "yellowgreen", 153: "blue",
##                  85: "brown", 86: "red", 87:"darkorange"}
##warning("uh")
##for k, v in color_table.items():
##    color_table[k] = pygame.Color(v)
##warning("uh oh")
# precalculated dictionary (crashes with pygame 1.8.1)
color_table = {99: (208, 32, 144, 255), 80: (34, 139, 34, 255), 81: (255, 215, 0, 255), 82: (255, 255, 255, 255), 83: (255, 105, 180, 255), 84: (105, 105, 105, 255), 85: (165, 42, 42, 255), 86: (255, 0, 0, 255), 87: (255, 140, 0, 255), 153: (0, 0, 255, 255), 122: (154, 205, 50, 255)}

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


class EntityView(object):

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

    def __setstate__(self, dictionary):
        self.__dict__.update(dictionary)   # update attributes
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
            for order_class in get_orders_list():
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
            self.interface.grid_view.display_attack(attacker_id, self)

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


from clientgameorder import OrderView, get_orders_list
