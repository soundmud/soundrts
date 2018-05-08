from lib.log import exception, warning, info
from lib.nofloat import PRECISION


COLLISION_RADIUS = 175 # millimeters # 350 / 2


class NotEnoughSpaceError(Exception): pass


class Entity(object):

    collision = 1
    place = None
    player = None
    menace = 0
    airground_type = "ground"
    bonus_height = 0
    activity = None
    blocked_exit = None
    building_land = None
    time_limit = None
    harm_level = 0

    qty = 0
    is_vulnerable = False
    is_repairable = False
    is_healable = False
    is_undead = False
    is_teleportable = False

    is_a_building_land =False

    transport_capacity = 0
    transport_volume = 99
    
    is_invisible = False
    is_cloakable = False
    is_cloaked = False
    sight_range = 85 * PRECISION / 10
    is_a_detector = False
    detection_range = 85 * PRECISION / 10
    is_a_cloaker = False
    cloaking_range = 6 * PRECISION

    id = None

    speed = 0
    is_moving = False

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    @property
    def is_memory(self):
        return hasattr(self, "time_stamp")

    _previous_square = None

    def move_to(self, new_place, x=None, y=None, o=90, exit1=None, exit2=None):
        if x is None:
            x = new_place.x
            y = new_place.y

        # make sure the object is not a memory
        if self.is_memory:
            warning("Will move the real object instead of its memorized version.")
            self.initial_model.move_to(new_place, x, y, o, exit1, exit2)
            return

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
                current_place.objects.remove(self)
                if current_place.__class__.__name__ == "Square":
                    self._previous_square = current_place
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
            else:
                # quit the world
                if self in current_place.world.active_objects:
                    current_place.world.active_objects.remove(self)
            # reactions
            if new_place is not None:
                self.action_target = None
        if self.place is not None and not self.is_inside and self.collision:
            self.world.collision[self.airground_type].add(self.x, self.y)
        if self.speed:
            self.is_moving = True

    def delete(self):
        self.unblock()
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

    def clean(self):
        self.__dict__ = {}

    def is_an_enemy(self, a):
        return False

    def notify(self, event, universal=False):
        if self.place is not None:
            for player in self.place.world.players:
                if self in player.perception or universal:
                    player.send_event(self, event)

    def would_collide_if(self, x, y):
        # optimization: same collision radius for every entity with collision
        if not self.collision:
            return False
        self.world.collision[self.airground_type].remove(self.x, self.y)
        result = self.world.collision[self.airground_type].would_collide(x, y)
        self.world.collision[self.airground_type].add(self.x, self.y)
        return result

    def contains(self, x, y):
        return True

    def find_free_space(self, airground_type, x, y, *args, **kargs):
        if self.transport_capacity: # the entity is a transport
            return x, y
        else:
            return None, None

    def block(self, e):
        self.blocked_exit = e
        e.add_blocker(self)

    def unblock(self):
        if self.blocked_exit:
            self.blocked_exit.remove_blocker(self)
            self.blocked_exit = None
