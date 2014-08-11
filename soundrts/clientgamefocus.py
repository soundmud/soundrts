from clientmediavoice import voice


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

    @property
    def id(self):
        sq = self.parent.place
        xstep = (sq.xmax - sq.xmin) / 3.0
        ystep = (sq.ymax - sq.ymin) / 3.0
        x = sq.x + self.x * xstep
        y = sq.y + self.y * ystep
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

    def select(self):
        self.parent.target = None
        self.parent.follow_mode = False

    def say(self):
        postfix = self.parent.square_postfix(self.parent.place)
        summary = self.parent.place_summary(self.parent.place, zoom=self)
        voice.item(self.title + postfix + summary)

    def contains(self, obj):
        sq = self.parent.place
        xstep = (sq.xmax - sq.xmin) / 3.0
        ystep = (sq.ymax - sq.ymin) / 3.0
        xmin = sq.xmin + (self.x + 1) * xstep
        xmax = xmin + xstep
        ymin = sq.ymin + (self.y + 1) * ystep
        ymax = ymin + ystep
        return  xmin <= obj.model.x < xmax and ymin <= obj.model.y < ymax