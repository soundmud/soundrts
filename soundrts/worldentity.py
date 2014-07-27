import sys
import time

from constants import COLLISION_RADIUS, USE_RANGE_MARGIN
from definitions import *
import worldrandom


class NotEnoughSpaceError(Exception): pass


class Entity(object):

    collision = 1
    place = None
    player = None
    menace = 0
    airground_type = "ground"
    activity = None

    qty = 0
    is_vulnerable = False
    is_repairable = False
    is_healable = False
    is_undead = False

    is_a_building_land =False

    transport_capacity = 0
    transport_volume = 99
    
    is_invisible = False
    is_cloakable = False
    is_a_detector = False
    is_a_cloaker = False

    id = None

    speed = 0
    is_moving = False

    @property
    def is_memory(self):
        return hasattr(self, "time_stamp")

    def update_all_dicts(self, inc):
        if getattr(self, "player", None) is not None:
            self.player.update_all_dicts(self, inc)

    def update_perception(self):
        try:
            for p in self.world.players:
                p.update_perception_of_object(self)
        except:
            exception("%s", self.type_name)

    def move_to(self, new_place, x=None, y=None, o=90, exit1=None, exit2=None):
        if x is None:
            x = new_place.x
            y = new_place.y

        # abort if there isn't enough space
        if new_place is not None and self.collision:
            if self.place is not None and not self.is_inside:
                self.world.collision[self.airground_type].remove(self.x, self.y)
            x, y = new_place.find_free_space(self.airground_type, x, y, new_place is self.place, self.player)
            if self.place is not None and not self.is_inside:
                self.world.collision[self.airground_type].add(self.x, self.y)
            if x is None:
                if self.place is not None:
                    return
                else:
                    raise NotEnoughSpaceError

        # move
        if self.place is not None and not self.is_inside and self.collision:
            self.world.collision[self.airground_type].remove(self.x, self.y)
        self.x = x
        self.y = y
        self.o = o
        if new_place is not self.place:
            current_place = self.place
            if current_place is not None:
                # quit the current place
                self.update_all_dicts(-1)
                current_place.objects.remove(self)
            self.place = new_place
            if new_place is not None:
                # enter the new place
                new_place.objects.append(self)
                if self.id is None: # new in the world
                    # enter the world
                    self.id = new_place.world.get_next_id()
                    new_place.world.objects[self.id] = self
                    if hasattr(self, "update"):
                        self.place.world.active_objects.append(self)
                self.update_all_dicts(1)
            else:
                # quit the world
                self.cible = None # probably unnecessary
                # (probably done by self.set_player(None))
                # (same remark for self.cancel_all_orders(), not done here)
                if self in current_place.world.active_objects:
                    current_place.world.active_objects.remove(self)
            # update perception
            self.update_perception()
            # reactions
            if new_place is not None:
                if current_place is not None:
                    for o in current_place.objects:
                        o.react_go_through(self, exit1)
                if self.is_vulnerable: # don't react to effects (?)
                    for p in self.world.players:
                        if p.is_an_enemy(self) and self in p.perception:
                            p.react_arrives(self, exit2)
                            for u in p.units:
                                u.react_arrives(self, exit2)
                self.cible = None
                self.react_self_arrival()
        if self.place is not None and not self.is_inside and self.collision:
            self.world.collision[self.airground_type].add(self.x, self.y)
        if self.speed:
            self.is_moving = True

    def delete(self):
        self.move_to(None, 0, 0)

    def __init__(self, place, x=None, y=None, o=90):
        self.world = place.world
        self.move_to(place, x, y, o)

    @property
    def is_inside(self):
        return getattr(self.place, "transport_capacity", 0)

    @property
    def radius(self):
        if self.collision:
            return COLLISION_RADIUS
        else:
            return 0

    def is_invisible_or_cloaked(self):
        return self.is_invisible or \
               self.is_cloakable and self.place in getattr(self.player, "cloaked_squares", [])

    def clean(self):
        self.__dict__ = {}

    def choose_enemy(self, someone=None):
        pass

    def react_go_through(self, other, door):
        pass
    def react_self_arrival(self):
        pass

    def react_death(self, creature):
        pass

    def is_an_enemy(self, a):
        return False

    def notify(self, event, universal=False):
        if self.place is not None:
            for player in self.place.world.players:
                if self in player.perception or universal:
                    player.send_event(self, event)

    def use_range(self, a): # use_distance? XXXXXXXXXXX
        if a.is_an_enemy(self) and a.range is not None:
            return max(a.radius + USE_RANGE_MARGIN, a.range) + self.radius
        else:
            return a.radius + self.radius + USE_RANGE_MARGIN

    def collision_range(self, a):
        if a.collision and self.collision and \
           self.airground_type == a.airground_type:
            return a.radius + self.radius
        else:
            return 0

    def would_collide_if(self, x, y):
        # optimization: same collision radius for every entity with collision
        if not self.collision:
            return False
        self.world.collision[self.airground_type].remove(self.x, self.y)
        result = self.world.collision[self.airground_type].would_collide(x, y)
        self.world.collision[self.airground_type].add(self.x, self.y)
        return result

    def be_used_by(self, a):
        a.cible = None
        a._flee_or_fight_if_enemy()

    def dans_le_mur(self, x, y):
        return False

    def find_free_space(self, airground_type, x, y, *args, **kargs):
        if self.transport_capacity: # the entity is a transport
            return x, y
        else:
            return None, None
