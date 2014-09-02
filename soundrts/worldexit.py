from nofloat import int_cos_1000, int_sin_1000
from worldentity import Entity


class Exit(Entity):

    other_side = None
    collision = 0
    is_an_exit = True

    def __init__(self, place, type_name):
        self.type_name = type_name
        place, x, y, o = place
        Entity.__init__(self, place, x, y, o)
        place.exits.append(self)
        self._blockers = []

    def is_blocked(self, o):
        for b in self._blockers + getattr(self.other_side, "_blockers", []):
            if not b.is_a_gate or o.is_an_enemy(b):
                return True

    @property
    def blockers(self):
        return self._blockers + getattr(self.other_side, "_blockers", [])

    def use_range(self, a):
        return a.radius + 1000 # + 10

    def be_used_by(self, actor):
        actor.move_to(self.other_side.place,
                      self.other_side.x + 250 * int_cos_1000(self.other_side.o) / 1000, # 25 cm
                      self.other_side.y + 250 * int_sin_1000(self.other_side.o) / 1000, # 25 cm
                      self.other_side.o,
                      self, self.other_side)

    def add_blocker(self, o):
        self._blockers.append(o)

    def remove_blocker(self, o):
        self._blockers.remove(o)


def passage(places, exit_type):
    place1, place2 = places
    exit1 = Exit(place1, exit_type)
    exit2 = Exit(place2, exit_type)
    exit1.other_side = exit2
    exit2.other_side = exit1
