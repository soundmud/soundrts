import math


##print "_cos_table = {}"
##print "_sin_table = {}"
##for a in range(360):
##    print "_cos_table[%s] = %s" % (a, int(math.cos(math.radians(a)) * 1000))
##    print "_sin_table[%s] = %s" % (a, int(math.sin(math.radians(a)) * 1000))

_cos_table = tuple(int(math.cos(math.radians(a)) * 1000) for a in range(360))
_sin_table = tuple(int(math.sin(math.radians(a)) * 1000) for a in range(360))
_acos_table = dict(((c, int(math.degrees(math.acos(c / 100.0)))) for c in range(-100, 101)))
print "_cos_table =", _cos_table
print "_sin_table =", _sin_table
print "_acos_table =", _acos_table
