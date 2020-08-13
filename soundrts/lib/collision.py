# from soundrts import version
DEBUG_MODE = False  # version.IS_DEV_VERSION


SHAPE = (
    (0, 0),
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    #            (1, 1), (-1, -1), (1, -1), (-1, 1),
)

##        BIG_SHAPE = (
##                    (0, 0),
##                    (1, 0), (-1, 0), (0, 1), (0, -1),
####                        (1, 1), (-1, -1), (1, -1), (-1, 1),
##                    (2, 0), (-2, 0), (0, 2), (0, -2),
####                        (2, 2), (-2, -2), (2, -2), (-2, 2),
##                    (3, 0), (-3, 0), (0, 3), (0, -3),
####                        (3, 3), (-3, -3), (3, -3), (-3, 3),
####                        (4, 0), (-4, 0), (0, 4), (0, -4),
####                        (4, 4), (-4, -4), (4, -4), (-4, 4),
##                 )


class CollisionMatrix:
    def __init__(self, xmax, res):
        if DEBUG_MODE:
            assert isinstance(xmax, int)
            assert isinstance(res, int)
        self._set = set()
        self.xmax = xmax
        self.res = res
        self.amax = self.xmax // self.res

    ##    def _key(self, x, y): # tuple variant
    ##        return x // self.res, y // self.res

    def _key(self, x, y):
        return x // self.res + self.amax * (y // self.res)

    ##    def _xy(self, k): # tuple variant
    ##        return (k[0] * self.res, k[1] * self.res)

    def _xy(self, k):
        b = k // self.amax
        a = k % self.amax
        return a * self.res, b * self.res

    def xy_set(self):
        return [self._xy(k) for k in self._set]

    ##    def _shape(self, x, y): # tuple variant
    ##        ka, kb = self._key(x, y)
    ##        return set(((ka + a, kb + b) for (a, b) in SHAPE))

    def _shape(self, x, y):
        if DEBUG_MODE:
            assert isinstance(x, int)
            assert isinstance(y, int)
            assert x >= 0
            assert x <= self.xmax
        k = self._key(x, y)
        return {k + a + self.amax * b for (a, b) in SHAPE}

    def would_collide(self, *args):
        return self._set.intersection(self._shape(*args))

    def add(self, *args):
        if DEBUG_MODE:
            assert not self.would_collide(*args)
        self._set.update(self._shape(*args))

    def remove(self, *args):
        if DEBUG_MODE:
            assert self._shape(*args).issubset(self._set)
        self._set.difference_update(self._shape(*args))


if __name__ == "__main__":
    m = CollisionMatrix(200, 2)
    #    assert m._key(0, 0) == 0
    print(m._key(50, 0))
    print(m._key(0, 50))
    for x, y in (
        (0, 0),
        (50, 0),
        (0, 50),
        (20, 56),
    ):
        k = m._key(x, y)
        print((x, y), k, m._xy(k))
        assert m._xy(k) == (x, y)
    for x, y in ((20, 57),):
        k = m._key(x, y)
        print((x, y), k, m._xy(k))
        assert m._xy(k) != (x, y)

    class O:
        collision = 1
        x = 6
        y = 6

    o = O()
    print(m._shape(o.x, o.y))
    assert len(m._shape(o.x, o.y)) in (5, 9)
    if m.would_collide(o.x, o.y):
        print("error")
    m.add(o.x, o.y)
    print(m.xy_set())
    #    m.add(o.x, o.y)
    if not m.would_collide(o.x, o.y):
        print("error")
    m.remove(o.x, o.y)
    if m.would_collide(o.x, o.y):
        print("error")
##    m.remove(o.x, o.y)
##    if m.would_collide(o.x, o.y):
##        print "error"
