import random
import time
from typing import List

import pygame

from . import config
from . import msgparts as mp
from .clientgamenews import must_be_said
from .clientgameorder import get_orders_list, substitute_args
from .clientmedia import sounds, voice
from .definitions import style
from .lib.log import exception, warning
from .lib.msgs import nb2msg
from .lib.nofloat import PRECISION
from .lib.sound import distance, psounds
from .worldunit import BuildingSite

# minimal interval (in seconds) between 2 sounds
FOOTSTEP_LIMIT = 0.1


def compute_title(type_name):
    t = style.get(type_name, "title")
    if t is None:
        return []
    else:
        return [int(x) for x in t]


def _order_title_msg(order, interface, nb=1):
    if order.is_deferred:
        result = style.get("messages", "production_deferred")
    else:
        result = []
    result += style.get(order.keyword, "title")
    if order.type is not None:
        t = style.get(order.type.type_name, "title")
        if nb != 1:
            t = nb2msg(nb) + t
        result = substitute_args(result, [t])
    if hasattr(order, "targets"):  # patrol
        for t in getattr(order, "targets"):
            result += EntityView(interface, t).title + mp.COMMA
    elif order.target is not None:
        if order.keyword == "build_phase_two":
            result += style.get(order.target.type.type_name, "title")
        else:
            result += EntityView(interface, order.target).title
    return mp.COMMA + result


class EntityView:

    next_step = None

    loop_noise = None
    loop_volume = 0
    loop_source = None

    repeat_noises: List[str] = []
    repeat_interval = -1
    repeat_source = None
    next_repeat = None

    def __init__(self, interface, model):
        self.interface = interface
        self.model = model
        self.footstep_random = (
            random.random() * 0.2
        )  # to avoid strange synchronicity of footsteps when several units are walking

    @property
    def footstep_interval(self):
        try:
            s = self.model.actual_speed
        except:
            s = self.model.speed
        return 1000.0 / s / 2 + self.footstep_random

    @property
    def when_moving_through(self):
        return style.get(self.model.type_name, "when_moving_through")

    @property
    def is_an_exit(self):
        return style.has(self.model.type_name, "when_moving_through")

    def is_in(self, place):
        # a unit inside a transporter is also inside the place of the transporter
        if getattr(self, "is_inside", False):
            return self.place.place is place
        # For the interface, a blocker is also on the other side of the exit.
        return (
            self.place is place
            or getattr(self, "blocked_exit", None)
            and self.blocked_exit.other_side.place is place
        )

    def __getattr__(self, name):
        v = getattr(self.model, name)
        if name in ["x", "y"]:
            v /= 1000.0
        elif name in ("qty", "hp", "hp_max", "mana", "mana_max"):
            v = int(v / PRECISION)
        return v

    def __getstate__(self):
        odict = self.__dict__.copy()  # copy the dict since we change it
        for k in ("loop_source", "repeat_source"):
            if k in odict:
                del odict[k]  # remove Sound entry
        return odict

    def __setstate__(self, dictionary):
        self.__dict__.update(dictionary)  # update attributes
        self.loop_source = None
        self.repeat_source = None

    @property
    def ext_title(self):
        try:
            return self.title + mp.AT + self.place.title
        except:
            exception("problem with %s.ext_title", self.type_name)

    def _menu(self, strict=False):
        menu = []
        try:  # TODO: remove this "try... except" when rules.txt checking is implemented
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
                    t += _order_title_msg(prev, self.interface, nb)
                    if o.keyword == "train":
                        prev = o
                        nb = 1
                    else:
                        t += _order_title_msg(o, self.interface)
                        prev = None
            elif o.keyword == "train":
                prev = o
                nb = 1
            else:
                t += _order_title_msg(o, self.interface)
            if o.keyword == "patrol":
                break
        if prev:
            t += _order_title_msg(prev, self.interface, nb)
        return t + mp.COMMA

    @property
    def title(self):
        if isinstance(self.model, BuildingSite):
            title = compute_title(self.type.type_name) + compute_title(
                BuildingSite.type_name
            )
        else:
            title = self.short_title[:]
        if self.player:
            if self.player == self.interface.player:
                title += nb2msg(self.number)
            else:
                if self.player in self.interface.player.allied:
                    title += mp.ALLY
                else:
                    title += mp.ENEMY
                title += mp.COMMA + self.player.name + mp.COMMA
        if self.is_memory:
            title += mp.IN_THE_FOG + mp.COMMA
            if self.speed:
                s = (self.world.time - self.time_stamp) // 1000
                m = s // 60
                if m:
                    title += nb2msg(m) + mp.MINUTES
                elif s:
                    title += nb2msg(s) + mp.SECONDS
                title += mp.COMMA
        return title

    @property
    def short_title(self):
        if self.type_name == "buildingsite":
            return compute_title(self.type.type_name) + compute_title(self.type_name)
        elif getattr(self, "level", 0) > 1:
            return compute_title(self.type_name) + mp.LEVEL + nb2msg(self.level)
        else:
            return compute_title(self.type_name)

    @property
    def hp_status(self):
        return nb2msg(self.hp) + mp.HITPOINTS_ON + nb2msg(self.hp_max)

    @property
    def mana_status(self):
        if self.mana_max > 0:
            return nb2msg(self.mana) + mp.MANA_POINTS_ON + nb2msg(self.mana_max)
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
                d += (
                    mp.COMMA
                    + mp.CONTAINS
                    + nb2msg(self.qty)
                    + style.get("parameters", "resource_%s_title" % self.resource_type)
                )
            if hasattr(self, "hp"):
                d += mp.COMMA + self.hp_status
            if hasattr(self, "mana"):
                d += mp.COMMA + self.mana_status
            if hasattr(self, "upgrades"):
                d += mp.COMMA + self.upgrades_status
            if getattr(self, "is_invisible", 0) or getattr(self, "is_cloaked", 0):
                d += mp.COMMA + mp.INVISIBLE
            if getattr(self, "is_a_detector", 0):
                d += mp.COMMA + mp.DETECTOR
            if getattr(self, "is_a_cloaker", 0):
                d += mp.COMMA + mp.CLOAKER
        except:
            pass  # a warning is given by style.get()
        return d

    def is_a_useful_target(self):
        # (useful for a worker)
        # resource deposits, building lands, damaged repairable units or buildings, blockable exits
        return (
            self.qty > 0
            or self.is_a_building_land
            or self.is_repairable
            and self.hp < self.hp_max
            or self.is_an_exit
        )

    def shape(self):
        shape = style.get(self.type_name, "shape", warn_if_not_found=False)
        if shape:
            return shape[0]

    def color(self):
        color = style.get(self.type_name, "color", warn_if_not_found=False)
        try:
            return pygame.Color(color[0])
        except:
            try:
                return (
                    255,
                    (int(self.short_title[0]) * int(self.short_title[0])) % 256,
                    int(self.short_title[0]) % 256,
                )
            except:
                return (255, 255, 255)

    def corrected_color(self):
        if self.model in self.interface.memory:
            return tuple([x // 2 for x in self.color()])
        else:
            return self.color()

    def _terrain_footstep(self):
        t = self.place.type_name
        if t:
            g = style.get(t, "ground")
            if g and style.has(self.type_name, "move_on_%s" % g[0]):
                return style.get(self.type_name, "move_on_%s" % g[0])

    def footstepnoise(self):
        # assert: "only immobile objects must be taken into account"
        result = style.get(self.type_name, "move")
        if self.airground_type == "ground" and self._terrain_footstep():
            return self._terrain_footstep()
        elif (
            self.airground_type == "ground" and len(self.place.objects) < 30
        ):  # save CPU
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
                    except KeyError:  # probably caused by the world client updates
                        continue
                    try:
                        d = distance(o.x, o.y, self.x, self.y) / k
                    except ZeroDivisionError:
                        continue
                    if d < d_min:
                        result = style.get(self.type_name, "move_on_%s" % g[0])
                        d_min = d
        return result

    def footstep(self):
        if self.is_moving and not self.is_memory:
            if self.next_step is None:
                self.step_side = 1
                self.next_step = (
                    time.time()
                    + random.random()
                    * self.footstep_interval
                    / self.interface.real_speed
                )  # start at different moments
            elif time.time() > self.next_step:
                if self.interface.immersion and (self.x, self.y) == (
                    self.interface.x,
                    self.interface.y,
                ):
                    v = 1 / 2.0
                else:
                    v = 1
                try:
                    self.launch_event(
                        self.footstepnoise()[self.step_side],
                        v,
                        priority=-10,
                        limit=FOOTSTEP_LIMIT,
                    )
                except IndexError:
                    pass
                self.next_step = (
                    time.time() + self.footstep_interval / self.interface.real_speed
                )
                self.step_side = 1 - self.step_side
        else:
            self.next_step = None

    def get_style(self, attr):
        st = style.get(self.type_name, attr)
        if st and st[0] == "if_me":
            if self.player in self.interface.player.allied:
                try:
                    return st[1 : st.index("else")]
                except ValueError:
                    return st[1:]
            else:
                try:
                    return st[st.index("else") + 1 :]
                except ValueError:
                    return []
        return st

    def _get_noise_style(self):
        if self.activity:
            st = self.get_style("noise_when_%s" % self.activity)
            if st:
                return st
        if hasattr(self, "hp"):
            if self.hp < self.hp_max / 3:
                st = self.get_style("noise_if_very_damaged")
                if st:
                    return st
            if self.hp < self.hp_max * 2 / 3:
                st = self.get_style("noise_if_damaged")
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
        if st[0] == "loop" and len(st) >= 2:
            self.loop_noise = st[1]
            try:
                self.loop_volume = float(st[2])
            except IndexError:
                self.loop_volume = 1
        elif st[0] == "repeat" and len(st) >= 3:
            self.repeat_interval = float(st[1])
            self.repeat_noises = st[2:]

    def update_noise(self):
        st = self._get_noise_style()
        self._set_noise(st)

    def launch_event_style(self, attr, alert=False, alert_if_far=False, priority=0):
        st = self.get_style(attr)
        if not st:
            return
        s = random.choice(st)
        if alert or alert_if_far and self.place is not self.interface.place:
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
                self.loop_source = psounds.play_loop(
                    sounds.get_sound(self.loop_noise),
                    self.loop_volume,
                    self.x,
                    self.y,
                    -10,
                )
            else:
                self.loop_source.move(self.x, self.y)
        else:
            self.stop()

    def _repeat_noise(self):
        if self.repeat_noises:
            if self.next_repeat is None:
                self.next_repeat = (
                    time.time() + random.random() * self.repeat_interval
                )  # to start at different moments
            # don't start a new "repeat sound" if the previous "repeat sound" hasn't stopped yet
            elif time.time() > self.next_repeat and getattr(
                self.repeat_source, "has_stopped", True
            ):
                self.repeat_source = self.launch_event(
                    random.choice(self.repeat_noises),
                    priority=-20,
                    ambient=self.ambient_noise,
                )
                self.next_repeat = time.time() + self.repeat_interval * (
                    0.8 + random.random() * 0.4
                )
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

    def stop(self):
        if self.loop_source is not None:
            self.loop_source.stop()
            self.loop_source = None

    previous_hp = None

    def _hp_noise(self, hp):
        return int(hp * 10 / self.hp_max)

    def render_hp_evolution(self):
        if self.previous_hp is not None:
            if self.hp < self.previous_hp or self._hp_noise(  # always noise if less HP
                self.hp
            ) != self._hp_noise(self.previous_hp):
                self.launch_event_style("proportion_%s" % self._hp_noise(self.hp))
            if self.hp > self.previous_hp and self.is_healable:
                self.launch_event_style("healed")

    def render_hp(self):
        if hasattr(self, "hp"):
            if self.is_dead:
                return  # TODO: remove this line (isolate the UI or use a deep copy of perception)
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
        self.launch_event_style("blocked")  # "blocked" is more precise than "collision"

    def on_attack(self):
        self.launch_event_style("attack", alert_if_far=True)

    def on_flee(self):
        self.launch_event_style("flee", alert_if_far=True)

    def on_store(self, resource_type):
        self.launch_event_style("store_resource_%s" % resource_type)

    def on_order_ok(self):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("order_ok", alert_if_far=True)

    def on_order_impossible(self, reason=None):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("order_impossible", alert_if_far=True)
        if reason is not None:
            voice.info(style.get("messages", reason))

    def on_production_deferred(self):
        voice.info(style.get("messages", "production_deferred"))

    def on_win_fight(self):
        self.launch_event_style("win_fight", alert_if_far=True)
        self.interface.units_alert_if_needed()

    def on_lose_fight(self):
        self.launch_event_style("lose_fight", alert_if_far=True)
        self.interface.units_alert_if_needed(place=self.place)

    def launch_event(self, sound, volume=1, priority=0, limit=0, ambient=False):
        if self.place is self.interface.place:
            pass
        elif self.place in getattr(self.interface.place, "neighbors", []):
            priority -= 1
            # Diminishing the volume is necessary as long as
            # "in the fog of war" squares are implemented
            # by shifting the observer backwards along the y axis.
            volume /= 4.0
        else:
            return
        return psounds.play(
            sounds.get_sound(sound), volume, self.x, self.y, priority, limit, ambient
        )

    def launch_alert(self, sound):
        self.interface.launch_alert(self.place, sound)

    def on_death_by(self, attacker_id):
        attacker = self.interface.dobjets.get(attacker_id)
        if self.player is self.interface.player:
            self.interface.lost_units.append([self.short_title, self.place])
        if getattr(attacker, "player", None) is self.interface.player:
            self.interface.neutralized_units.append(
                [self.short_title, self.place]
            )  # TODO: "de " self.player.name
        friends = [
            u for u in self.player.units if u.place is self.place and u.id != self.id
        ]
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
        if (
            self.interface.previous_unit_attacked_alert is None
            or time.time() > self.interface.previous_unit_attacked_alert + 10
        ):
            self.launch_event_style("alert", alert_if_far=True)
            self.interface.previous_unit_attacked_alert = time.time()

    def on_wounded(self, attacker_type, attacker_id, level):
        if self.player == self.interface.player:
            self.unit_attacked_alert()
        s = style.get(attacker_type, "attack_hit_level_%s" % level)
        if s is not None:
            if s:
                self.launch_event(random.choice(s))
        else:
            warning(
                "no sound found for: %s %s",
                attacker_type,
                "attack_hit_level_%s" % level,
            )
        if self.interface.display_is_active and attacker_id in self.interface.dobjets:
            self.interface.grid_view.display_attack(attacker_id, self)

    def on_exhausted(self):
        self.launch_event_style("exhausted")
        if "resource_exhausted" in config.verbosity:
            voice.info(self.title + mp.EXHAUSTED)

    def on_completeness(self, s):  # building train or upgrade
        self.launch_event_style("production")
        self.launch_event_style("proportion_%s" % s)

    def on_complete(self):
        if self.player is not self.interface.player:
            return
        self.launch_event_style("complete", alert_if_far=True)
        if "unit_complete" in config.verbosity and must_be_said(self.number):
            voice.info(substitute_args(self.get_style("complete_msg"), [self.title]))
        self.interface.send_menu_alerts_if_needed()  # not necessary for "on_repair_complete" (if it existed)

    def on_research_complete(self):
        voice.info(self.get_style("research_complete_msg"))
        self.interface.send_menu_alerts_if_needed()

    def on_added(self):
        self.launch_event_style("added", alert_if_far=True)
        if "unit_added" in config.verbosity and must_be_said(self.number):
            voice.info(substitute_args(self.get_style("added_msg"), [self.ext_title]))

    def on_level_up(self):
        if self.player is self.interface.player:
            self.launch_event_style("level_up", alert_if_far=True, priority=10)
            if self.id in self.interface.group:
                self.launch_event_style("level_up", alert=True, priority=10)
        else:
            self.launch_event_style("level_up", priority=10)

    def on_upgrade_to(self, new_id):
        self.on_level_up()
        if self.id in self.interface.group:
            self.interface.group.remove(self.id)
            self.interface.group.append(new_id)

    def on_buff(self, event, buff, msg=None):
        st = style.get(buff, event)
        if st:
            s = random.choice(st)
            self.launch_event(s)
        if msg and self.player is self.interface.player:
            voice.info([msg])

    def on_cooldown_end(self, ability):
        if self.player is self.interface.player:
            st = style.get(ability, "cooldown_end")
            if st:
                s = random.choice(st)
                self.launch_event(s)
