from .lib.log import warning
from .lib.nofloat import PRECISION

COLLISION_RADIUS = 175  # millimeters # 350 / 2


class NotEnoughSpaceError(Exception):
    pass


class Entity:

    collision = 1
    place = None
    x = 0
    y = 0
    o = 0
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

    is_a_building_land = False

    transport_capacity = 0
    transport_volume = 99

    is_invisible = False
    is_cloakable = False
    is_cloaked = False
    sight_range = 85 * PRECISION // 10
    is_a_detector = False
    detection_range = 85 * PRECISION // 10
    is_a_cloaker = False
    cloaking_range = 6 * PRECISION

    id = None

    speed = 0
    speed_on_terrain = ()
    is_moving = False

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    @property
    def is_memory(self):
        return hasattr(self, "time_stamp")

    @property
    def is_near_water(self):
        return getattr(self.place, "is_near_water", False)

    _previous_square = None

    def move_to(self, new_place, x=None, y=None, o=90):
        if x is None:
            x = new_place.x
            y = new_place.y

        # make sure the object is not a memory
        if self.is_memory:
            warning("Will move the real object instead of its memorized version.")
            self.initial_model.move_to(new_place, x, y, o)
            return

        # abort if there isn't enough space
        if new_place and self.collision:
            x, y = new_place.find_free_space_for(self, x, y)
            if x is None:
                if self.place:
                    return
                else:
                    raise NotEnoughSpaceError

        # move
        if self.collision:
            self.free_space()
        self.x = x
        self.y = y
        self.o = o
        if new_place is not self.place:
            self._move_to_new_place(new_place)
        if self.collision:
            self.occupy_space()
        if self.speed:
            self.is_moving = True

    def _move_to_new_place(self, new_place):
        if self.place:
            self.place.leave(self)
            if not new_place:
                self.place.world.unregister_entity(self)
        self._previous_square = self.place
        self.place = new_place
        if new_place:
            new_place.enter(self)
            # reactions
            self.action_target = None

    def occupy_space(self):
        if self.place:
            self.place.add(self)

    def free_space(self):
        if self.place:
            self.place.remove(self)

    def delete(self):
        self.unblock()
        self.move_to(None, 0, 0)

    def __init__(self, place, x=None, y=None, o=90):
        self.world = place.world
        self.move_to(place, x, y, o)

    @property
    def is_inside(self):
        return self.place.__class__.__name__ == "Inside"

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
        if self.is_inside:
            emitter = self.place.container
        else:
            emitter = self
        if emitter.place:
            for player in emitter.place.world.players:
                if emitter in player.perception or universal:
                    player.send_event(emitter, event)

    def would_collide_if(self, x, y):
        # optimization: same collision radius for every entity with collision
        if self.collision:
            return self.place.would_collide(self, x, y)

    def contains(self, x, y):
        return True

    def block(self, e):
        self.blocked_exit = e
        e.add_blocker(self)

    def unblock(self):
        if self.blocked_exit:
            self.blocked_exit.remove_blocker(self)
            self.blocked_exit = None

    @property
    def any_land(self):
        for s in self.place.subsquares:
            if s.contains(self.x, self.y):
                return s.any_land
