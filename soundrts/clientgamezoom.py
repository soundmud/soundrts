from clientmediavoice import voice
from msgs import nb2msg


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

    def say(self):
        voice.item(self.parent.place.title + _subzone_name[(self.x, self.y)])
