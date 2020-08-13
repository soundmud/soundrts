import copy

from .lib.nofloat import PRECISION, to_int
from .worldentity import Entity


class Deposit(Entity):

    resource_type = None
    extraction_time = None
    extraction_qty = None
    resource_regen = 0

    def __init__(self, prototype, square, qty):
        prototype.init_dict(self)
        self.qty = to_int(
            qty
        )  # does the value come from the map? (already done in rules)
        self.qty_max = self.qty
        if self.resource_type == 1:  # wood
            self.resource_regen = to_int(".01")
        Entity.__init__(self, square)

    def extract_resource(self):
        self.qty -= self.extraction_qty
        if self.qty <= 0:
            self.die()

    def die(self):
        place, x, y = self.place, self.x, self.y
        self.notify("exhausted")
        self.delete()
        if self.building_land:
            self.building_land.move_to(place, x, y)

    def update(self):
        pass  # necessary to allow slow update

    def slow_update(self):
        if self.resource_regen and self.qty < self.qty_max:
            self.qty = min(self.qty + self.resource_regen, self.qty_max)


class BuildingLand(Entity):

    is_a_building_land = True
    collision = 0


class Meadow(BuildingLand):

    type_name = "meadow"


class Corpse(Entity):

    type_name = "corpse"
    collision = 0

    def __init__(self, unit):
        self.unit = copy.copy(unit)
        Entity.__init__(self, unit.place, unit.x, unit.y)
        self.time_limit = self.place.world.time + 300 * PRECISION

    def update(self):
        pass  # necessary to allow slow update

    def slow_update(self):
        if self.place.world.time >= self.time_limit:
            self.delete()
