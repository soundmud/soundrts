from .lib.log import warning
from .worldentity import Entity


class Exit(Entity):

    other_side: "Exit"
    collision = 0
    is_a_building_land = False
    is_an_exit = True

    def __init__(self, place, type_name, is_a_portal):
        self.type_name = type_name
        self.is_a_portal = is_a_portal
        place, x, y, o = place
        Entity.__init__(self, place, x, y, o)
        place.exits.append(self)
        self._blockers = []

    def __repr__(self):
        try:
            return "<Exit to '%s'>" % self.other_side.place.name
        except:
            return "<Exit to nowhere>"

    is_blocked_by_forests = False

    def is_blocked(self, o=None, ignore_enemy_walls=False, ignore_forests=False):
        if not ignore_forests and self.is_blocked_by_forests:
            return True
        for b in self._blockers + getattr(self.other_side, "_blockers", []):
            if ignore_enemy_walls and (o is None or o.is_an_enemy(b)):
                continue
            if not b.is_a_gate or (o is None or o.is_an_enemy(b)):
                return True

    @property
    def blockers(self):
        return self._blockers + getattr(self.other_side, "_blockers", [])

    def add_blocker(self, o):
        self._blockers.append(o)

    def remove_blocker(self, o):
        self._blockers.remove(o)

    def delete(self):
        self.place.exits.remove(self)
        if self.other_side:
            self.other_side.other_side = None
            self.other_side.delete()
        Entity.delete(self)


def passage(places, exit_type):
    place1, place2, is_a_portal = places
    if place1[0].is_water != place2[0].is_water:
        warning(f"removed amphibious path between {place1[0]} and {place2[0]}")
        return
    exit1 = Exit(place1, exit_type, is_a_portal)
    exit2 = Exit(place2, exit_type, is_a_portal)
    exit1.other_side = exit2
    exit2.other_side = exit1
