from clientmediascreen import draw_rect
from clientmediavoice import voice
from nofloat import PRECISION


_subzone_name = {
    (0, 0): [],
    (0, 1): [67],
    (0, -1): [68],
    (1, 0): [69],
    (-1, 0): [70],
    (1, 1): [71],
    (-1, 1): [72],
    (1, -1): [73],
    (-1, -1): [74],
    }


class Zoom(object):

    x = 0
    y = 0

    def __init__(self, parent):
        self.parent = parent
        sq = self.parent.place
        self.xstep = (sq.xmax - sq.xmin) / 3.0
        self.ystep = (sq.ymax - sq.ymin) / 3.0
        self.update_coords()

    @property
    def id(self):
        sq = self.parent.place
        x = sq.x + self.x * self.xstep
        y = sq.y + self.y * self.ystep
        return "zoom-%s-%s-%s" % (sq.id, int(x), int(y))

    @property
    def title(self):
        return self.parent.place.title + _subzone_name[(self.x, self.y)]

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        if self.x == 2:
            self.x = -1
            self.parent.place = self.parent._compute_move(1, 0)
        elif self.x == -2:
            self.x = 1
            self.parent.place = self.parent._compute_move(-1, 0)
        elif self.y == 2:
            self.y = -1
            self.parent.place = self.parent._compute_move(0, 1)
        elif self.y == -2:
            self.y = 1
            self.parent.place = self.parent._compute_move(0, -1)
        self.update_coords()
        self.parent.set_obs_pos()

    def select(self):
        self.parent.target = None
        self.parent.follow_mode = False

    def say(self):
        postfix = self.parent.square_postfix(self.parent.place)
        summary = self.parent.place_summary(self.parent.place, zoom=self)
        voice.item(self.title + postfix + summary)

    def update_coords(self):
        sq = self.parent.place
        self.xmin = sq.xmin + (self.x + 1) * self.xstep
        self.xmax = self.xmin + self.xstep
        self.ymin = sq.ymin + (self.y + 1) * self.ystep
        self.ymax = self.ymin + self.ystep

    def contains(self, obj):
        return  self.xmin <= obj.model.x < self.xmax and self.ymin <= obj.model.y < self.ymax
    
    def display(self, grid):
        xmin, ymin = grid.xy_coords(self.xmin, self.ymin)
        xmax, ymax = grid.xy_coords(self.xmax, self.ymax)
        if self.parent.target is None:
            color = (255, 255, 255)
        else:
            color = (150, 150, 150)
        draw_rect(color, xmin, ymin, xmax - xmin, ymax - ymin, 1)

    def obs_pos(self):
        x = (self.xmin + self.xmax) / 2.0
        y = self.ymin + (self.ymax - self.ymin) / 8.0
        if self.parent.place not in self.parent.scouted_squares:
            y -= self.ymax - self.ymin # lower sounds if fog of war
        return x / PRECISION, y / PRECISION
