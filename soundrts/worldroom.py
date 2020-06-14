from __future__ import absolute_import
from __future__ import division
import string

from .lib.msgs import nb2msg
from .lib.nofloat import int_distance, int_angle, int_cos_1000, int_sin_1000
from .lib.priodict import priorityDictionary
from .worldentity import COLLISION_RADIUS
from .worldexit import passage
from .worldresource import Deposit, Meadow


SPACE_LIMIT = 144

def square_spiral(x, y, step=COLLISION_RADIUS * 25 // 10):
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


_cache = {}
_cache_time = None


def cache(f):
    def decorated_f(*args, **kargs):
        global _cache, _cache_time
        if _cache_time != args[0].world.time:
            _cache = {}
            _cache_time = args[0].world.time
        k = (args, tuple(sorted(kargs.items())))
        if k not in _cache:
            _cache[k] = f(*args, **kargs)   
        return _cache[k]
    return decorated_f


class Square(object):

    transport_capacity = 0
    type_name = ""
    terrain_speed = (100, 100)
    terrain_cover = (0, 0)
    is_ground = True
    is_water = False
    is_air = True

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
        self.x = (self.xmax + self.xmin) // 2
        self.y = (self.ymax + self.ymin) // 2

    def __repr__(self):
        return "<'%s'>" % self.name

    @property
    def height(self):
        if self.high_ground:
            return 1
        else:
            return 0

    @property
    def strict_neighbors(self):
        result = []
        for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            s = self.world.grid.get((self.col + dc, self.row + dr))
            if s is not None:
                result.append(s)
        return result
 

    def set_neighbors(self):
        result = []
        for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            s = self.world.grid.get((self.col + dc, self.row + dr))
            if s is not None:
                result.append(s)
        self.neighbors = result

    @property
    def building_land(self):
        for o in self.objects:
            if o.is_a_building_land:
                return o

    @property
    def is_near_water(self):
        if not self.is_ground or self.high_ground:
            return False
        for sq in self.strict_neighbors:
            if sq.is_water:
                return True

    def __getstate__(self):
        d = self.__dict__.copy()
        if 'spiral' in d:
            del d['spiral']
        if 'neighbors' in d:
            del d['neighbors']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def is_near(self, square):
        try:
            return (abs(self.col - square.col), abs(self.row - square.row)) in ((0, 1), (1, 0), (1, 1))
        except AttributeError: # not a square
            return False

    def clean(self):
        for o in self.objects:
            o.clean()
        self.__dict__ = {}

    def contains(self, x, y):
        return self.xmin <= x < self.xmax and \
               self.ymin <= y < self.ymax

    def shortest_path_to(self, dest, player=None, plane="ground", places=False, avoid=False):
        if places:
            return self._shortest_path_to(dest, plane, player, places=True, avoid=avoid)
        else:
            return self._shortest_path_to(dest, plane, player, avoid=avoid)[0]

    def shortest_path_distance_to(self, dest, player=None, plane="ground", avoid=False):
        return self._shortest_path_to(dest, plane, player, avoid=avoid)[1]

    @cache
    def _shortest_path_to(self, dest, plane, player, places=False, avoid=False):
        """Returns the next exit to the shortest path from self to dest
        and the distance of the shortest path from self to dest."""
        # TODO: remove the duplicate exits in the graph
        if avoid:
            avoid = player.is_very_dangerous
        else:
            avoid = lambda x: False
        if dest is self:
            return [self] if places else (None, 0)
##        if not dest.exits: # small optimization
##            return None, None # no path exists

        # add start and end to the graph
        G = self.world.g[plane]
        if plane == "ground":
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
            if hasattr(v, "is_blocked") and v.is_blocked(player, ignore_enemy_walls=True) or avoid(v):
                continue
            D[v] = Q[v][0]
            if v == end: break
            
            for w in G[v]:
                if hasattr(w, "is_blocked") and w.is_blocked(player, ignore_enemy_walls=True) or avoid(w):
                    continue
                vwLength = D[v] + G[v][w]
                if w in D:
                    pass
                elif w not in Q or vwLength < Q[w][0]:
                    Q[w] = (vwLength, int(w.id),) # the additional value makes the result "cross-machine deterministic"
                    P[w] = v

        # restore the graph
        if plane == "ground":
            for v in (start, end):
                del G[v]
                for e in v.exits:
                    del G[e][v]

        # exploit the results
        if end not in P:
            # no path exists
            return [] if places else (None, None)
        Path = []
        while 1:
            Path.append(end)
            if end == start: break
            end = P[end]
        Path.reverse()
        if places:
            return [e.place for e in Path if hasattr(e, "other_side")]
        else:
            return Path[1], D[dest]

    def find_nearest_meadow(self, unit):
        def _d(o):
            # o.id to make sure that the result is the same on any computer
            return (int_distance(o.x, o.y, unit.x, unit.y), o.id)
        meadows = sorted([o for o in self.objects if isinstance(o, Meadow)], key=_d)
        if meadows:
            return meadows[0]
        
    def find_and_remove_meadow(self, item_type):
        if item_type.is_buildable_anywhere:
            return self.x, self.y, None
        for o in self.objects:
            if isinstance(o, Meadow):
                x, y = o.x, o.y
                o.delete()
                return x, y, o
        return self.x, self.y, None

    def contains_enemy(self, player):
        for o in self.objects:
            if player.is_an_enemy(o):
                return True
        return False
        
    def north_side(self):
        return self, self.x, self.ymax - 1, -90

    def south_side(self):
        return self, self.x, self.ymin, 90

    def east_side(self):
        return self, self.xmax - 1, self.y, 180

    def west_side(self):
        return self, self.xmin, self.y, 0

    def _shift(self, xc, yc):
        # shift angle to have central symmetry and map balance
        # (distance from the townhall to the resources)
        return int_angle(xc, yc, self.col * 10 + 5, self.row * 10 + 5)

    def arrange_resources_symmetrically(self, xc, yc):
        things = [o for o in self.objects if isinstance(o, (Deposit, Meadow))]
        square_width = self.xmax - self.xmin
        nb = len(things)
        shift = self._shift(xc, yc)
        for i, o in enumerate(things):
            x = self.x
            y = self.y
            if nb > 1:
                a = 360 * i // nb + shift
                # it is possible to add a constant to this angle and keep
                # the symmetry
                x += square_width * 35 // 100 * int_cos_1000(a) // 1000
                y += square_width * 35 // 100 * int_sin_1000(a) // 1000
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
                self.spiral["water"] = square_spiral(x, y)
            spiral = self.spiral[airground_type] # reuse spiral (don't retry used places: much faster!)
        else:
            spiral = square_spiral(x, y)
        for x, y in spiral:
            if self.contains(x, y) and \
               not self.world.collision[airground_type].would_collide(x, y):
                return x, y
        return None, None

    def ensure_path(self, other):
        if other not in [e.other_side.place for e in self.exits]:
            x = (self.x + other.x) // 2
            y = (self.y + other.y) // 2
            passage(((self, x, y, 0), (other, x, y, 0), False), "path")
            self.world._create_graphs()

    def ensure_nopath(self, other):
        for e in self.exits:
            if other == e.other_side.place:
                e.delete()

    def toggle_path(self, dc, dr):
        other = self.world.grid.get((self.col + dc, self.row + dr))
        if not other: # border
            return
        if other in [e.other_side.place for e in self.exits]:
            self.ensure_nopath(other)
        else:
            self.ensure_path(other)
            return True

    def ensure_meadows(self, n):
        for o in self.objects[:]:
            if n >= self.nb_meadows:
                break
            if o.is_a_building_land and not getattr(o, "is_an_exit", False):
                o.delete()
        for _ in range(n - self.nb_meadows):
            Meadow(self)
        self.arrange_resources_symmetrically(self.x, self.y)

    def ensure_resources(self, t, n, q):
        for o in self.objects[:]:
            if o.type_name == t:
                o.delete()
        for _ in range(n):
            self.world.unit_class(t)(self, q)

    @property
    def nb_meadows(self):
        return len([o for o in self.objects if o.is_a_building_land and not getattr(o, "is_an_exit", False) or o.building_land and not getattr(o, "qty", 0)])

    def update_terrain(self):
        meadows = len([o for o in self.objects if o.type_name == "meadow"])
        woods = len([o for o in self.objects if o.type_name == "wood"])
        if woods >= 3:
            self.type_name = "_dense_forest"
        elif woods:
            self.type_name = "_forest"
        elif meadows:
            self.type_name = "_meadows"
        else:
            self.type_name = ""
        # dynamic path through forest
        if self.type_name == "_dense_forest":
            for s in self.strict_neighbors:
                if s.type_name == "_dense_forest":
                    self.ensure_nopath(s)
                elif s.high_ground == self.high_ground:
                    self.ensure_path(s)
