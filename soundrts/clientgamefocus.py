from . import msgparts as mp
from .lib.log import warning
from .lib.nofloat import PRECISION
from .lib.voice import voice

_subzone_name = {
    (0, 0): mp.AT_THE_CENTER,
    (0, 1): mp.NORTH,
    (0, -1): mp.SOUTH,
    (1, 0): mp.EAST,
    (-1, 0): mp.WEST,
    (1, 1): mp.NORTHEAST,
    (-1, 1): mp.NORTHWEST,
    (1, -1): mp.SOUTHEAST,
    (-1, -1): mp.SOUTHWEST,
    }


class Zoom:

    sub_x = 0
    sub_y = 0

    def __init__(self, parent):
        self.parent = parent
        sq = self.parent.place
        self.xstep = (sq.xmax - sq.xmin) / 3.0
        self.ystep = (sq.ymax - sq.ymin) / 3.0
        self.update_coords()

    @property
    def id(self):
        sq = self.parent.place
        x = sq.x + self.sub_x * self.xstep
        y = sq.y + self.sub_y * self.ystep
        return "zoom-{}-{}-{}".format(sq.id, int(x), int(y))

    @property
    def title(self):
        return self.parent.place.title + _subzone_name[(self.sub_x, self.sub_y)]

    def move(self, dx, dy):
        self.parent.follow_mode = False # or set_obs_pos() will cause trouble
        self.sub_x += dx
        self.sub_y += dy
        if self.sub_x >= 2:
            self.sub_x = -1
            self.parent.place = self.parent._compute_move(1, 0)
        elif self.sub_x <= -2:
            self.sub_x = 1
            self.parent.place = self.parent._compute_move(-1, 0)
        elif self.sub_y >= 2:
            self.sub_y = -1
            self.parent.place = self.parent._compute_move(0, 1)
        elif self.sub_y <= -2:
            self.sub_y = 1
            self.parent.place = self.parent._compute_move(0, -1)
        self.update_coords()
        self.parent.set_obs_pos()

    def move_to(self, o):
        self.parent.place = o.place
        for self.sub_x, self.sub_y in list(_subzone_name.keys()):
            self.update_coords()
            if self.contains(o):
                self.parent.set_obs_pos()
                break
        if not self.contains(o):
            warning("zoom: couldn't move to object")
        
    def select(self):
        self.parent.target = None
        self.parent.follow_mode = False

    def say(self, prefix=[]):
        postfix = self.parent.square_postfix(self.parent.place)
        summary = self.parent.place_summary(self.parent.place, zoom=self)
        voice.item(prefix + self.title + postfix + summary)

    def update_coords(self):
        sq = self.parent.place
        self.xmin = sq.xmin + (self.sub_x + 1) * self.xstep
        self.xmax = self.xmin + self.xstep
        self.ymin = sq.ymin + (self.sub_y + 1) * self.ystep
        self.ymax = self.ymin + self.ystep

    def contains(self, obj):
        return self.xmin <= obj.model.x < self.xmax and self.ymin <= obj.model.y < self.ymax

    def obs_pos(self):
        x = (self.xmin + self.xmax) / 2.0
        y = self.ymin + (self.ymax - self.ymin) / 8.0
        if self.parent.place not in self.parent.scouted_squares:
            y -= self.ymax - self.ymin # lower sounds if fog of war
        return x / PRECISION, y / PRECISION
