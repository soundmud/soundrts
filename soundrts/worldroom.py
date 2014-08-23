import string

from constants import COLLISION_RADIUS
from msgs import nb2msg
from nofloat import int_distance, int_angle, int_cos_1000, int_sin_1000
from priodict import priorityDictionary
from worldresource import Meadow


SPACE_LIMIT = 144

def square_spiral(x, y, step=COLLISION_RADIUS * 25 / 10):
    yield x, y
    sign = 1
    delta = 1
    while delta < 25:
        for _ in range(delta):
            x += sign * step
            yield x, y
        for _ in range(delta):
            y += sign * step
            yield x, y
        delta += 1
        sign *= -1


class Square(object):

    transport_capacity = 0

    def __init__(self, world, col, row, width):
        self.col = col
        self.row = row
        self.name = "%s%s" % (string.ascii_lowercase[col], row + 1)
        self.id = world.get_next_id()
        self.world = world
        world.squares.append(self)
        world.objects[self.id] = self
        self.place = world
        self.title = [5000 + col] + nb2msg(row + 1)
        self.objects = []
        self.exits = []
        self.xmin = col * width
        self.ymin = row * width
        self.xmax = self.xmin + width
        self.ymax = self.ymin + width
        self.x = (self.xmax + self.xmin) / 2
        self.y = (self.ymax + self.ymin) / 2


    @property
    def height(self):
        if self.high_ground:
            return 1
        else:
            return 0

    @property
    def neighbours(self):
        result = []
        for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            s = self.world.grid.get((self.col + dc, self.row + dr))
            if s is not None:
                result.append(s)
        return result

    @property
    def building_land(self):
        for o in self.objects:
            if o.is_a_building_land:
                return o

    def __getstate__(self):
        odict = self.__dict__.copy() # copy the dict since we change it
        if odict.has_key('spiral'):
            del odict['spiral'] # remove "spiral" entry (cf find_free_space())
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)   # update attributes

    def is_near(self, square):
        try:
            return (abs(self.col - square.col), abs(self.row - square.row)) in ((0, 1), (1, 0))
        except AttributeError: # not a square
            return False

    def clean(self):
        for o in self.objects:
            o.clean()
        self.__dict__ = {}

    def contains(self, x, y):
        return self.xmin <= x <= self.xmax and \
               self.ymin <= y <= self.ymax

    def shortest_path_to(self, dest):
##        if len(self.exits) == 1: # small optimization
##            return self.exits[0]
        return self._shortest_path_to(dest)[0]

    def shortest_path_distance_to(self, dest):
        return self._shortest_path_to(dest)[1]

    def _shortest_path_to(self, dest):
        """Returns the next exit to the shortest path from self to dest
        and the distance of the shortest path from self to dest."""
        # TODO: remove the duplicate exits in the graph
        if dest is self:
            return None, 0
##        if not dest.exits: # small optimization
##            return None, None # no path exists

        # add start and end to the graph
        G = self.world.g
        for v in (self, dest):
            G[v] = {}
            for e in v.exits:
                G[v][e] = G[e][v] = int_distance(v.x, v.y, e.x, e.y)
        start = self
        end = dest

        # apply Dijkstra's algorithm (with priority list)
        D = {}        # dictionary of final distances
        P = {}        # dictionary of predecessors
        Q = priorityDictionary()   # est.dist. of non-final vert.
        Q[start] = (0, )

        for v in Q:
            D[v] = Q[v][0]
            if v == end: break
            
            for w in G[v]:
                vwLength = D[v] + G[v][w]
                if w in D:
                    pass
                elif w not in Q or vwLength < Q[w][0]:
                    Q[w] = (vwLength, int(w.id),) # the additional value makes the result "cross-machine deterministic"
                    P[w] = v

        # restore the graph
        for v in (start, end):
            del G[v]
            for e in v.exits:
                del G[e][v]

        # exploit the results
        if end not in P:
            return None, None # no path exists
        Path = []
        while 1:
            Path.append(end)
            if end == start: break
            end = P[end]
        Path.reverse()
        return Path[1], D[dest]

    combat = False
    lcombattants = []
    last_information = 0

    def find_nearest_meadow(self, unit):
        def _d(o):
            # o.id to make sure that the result is the same on any computer
            return (int_distance(o.x, o.y, unit.x, unit.y), o.id)
        meadows = sorted([o for o in self.objects if isinstance(o, Meadow)], key=_d)
        if meadows:
            return meadows[0]
        
    def find_and_remove_meadow(self, item_type):
        if item_type.is_buildable_anywhere:
            return self.x, self.y
        for o in self.objects:
            if isinstance(o, Meadow):
                x, y = o.x, o.y
                o.delete()
                return x, y
        return self.x, self.y

    def update_menace(self):
        self.menace = {}
        for player in self.world.players:
            self.menace[player] = 0
        for o in self.objects:
            if hasattr(o, "player"):
                if self.menace.has_key(o.player):
                    self.menace[o.player] += o.menace
                else:
                    self.menace[o.player] = o.menace

    def contains_enemy(self, player):
        for o in self.objects:
            if hasattr(o, "player") and player.is_an_enemy(o):
                return True
        return False
        
    def balance(self, player):
        self.update_menace()
        balance = 0
        for p in self.world.players:
            if p.is_an_enemy(player):
                balance -= self.menace[p]
            elif p in player.allied:
                balance += self.menace[p]
        return balance

    def north_side(self):
        return self, self.x, self.ymax, -90

    def south_side(self):
        return self, self.x, self.ymin, 90

    def east_side(self):
        return self, self.xmax, self.y, 180

    def west_side(self):
        return self, self.xmin, self.y, 0

    def _shift(self, xc, yc):
        # shift angle to have central symmetry and map balance
        # (distance from the townhall to the resources)
        return int_angle(xc, yc, self.col * 10 + 5, self.row * 10 + 5)

    def arrange_resources_symmetrically(self, xc, yc):
        square_width = self.xmax - self.xmin
        nb = len(self.objects)
        shift = self._shift(xc, yc)
        for i, o in enumerate(self.objects):
            x = self.x
            y = self.y
            if nb > 1:
                a = 360 * i / nb + shift
                # it is possible to add a constant to this angle and keep
                # the symmetry
                x += square_width * 35 / 100 * int_cos_1000(a) / 1000
                y += square_width * 35 / 100 * int_sin_1000(a) / 1000
            o.move_to(o.place, x, y)

    def can_receive(self, airground_type, player=None):
        if player is not None:
            f = player.is_an_enemy
        else:
            f = lambda x: False
        return len([u for u in self.objects if u.collision
                    and u.airground_type == airground_type
                    and not f(u)]) < SPACE_LIMIT

    def find_free_space(self, airground_type, x, y, same_place=False, player=None):
        # assertion: object has collision
##        if not same_place and not self.can_receive(airground_type, player):
##            return None, None
        if self.contains(x, y) and \
           not self.world.collision[airground_type].would_collide(x, y):
            return x, y
        if self.world.time == 0 and (x, y) == (self.x, self.y):
            if not hasattr(self, "spiral"):
                self.spiral = {}
                self.spiral["ground"] = square_spiral(x, y)
                self.spiral["air"] = square_spiral(x, y)
            spiral = self.spiral[airground_type] # reuse spiral (don't retry used places: much faster!)
        else:
            spiral = square_spiral(x, y)
        for x, y in spiral:
            if self.contains(x, y) and \
               not self.world.collision[airground_type].would_collide(x, y):
                return x, y
        return None, None
