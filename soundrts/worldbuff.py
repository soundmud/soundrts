# TODO: buff name in unit status
# TODO: buff noise while active
# TODO: use world.time instead? (no update of time_left all the time)
from soundrts.definitions import VIRTUAL_TIME_INTERVAL
from soundrts.lib.log import warning
from soundrts.lib.nofloat import PRECISION, to_int

ALLOWED_STATS = """
hp hp_max hp_regen mana mana_max mana_regen
speed damage cooldown armor range minimal_range splash
damage_radius minimal_damage harm_level heal_level
""".split()

# The following stats would require specific code:
# - food_cost (used food should be updated by the player)
# - damage_level (the damage would need to be updated with the damage bonus)
# - revival_time (temporary buffs are removed after death)


class Buff:
    is_a = ()  # silence warning
    expanded_is_a = ()  # silence warning

    duration = 0
    stack = 0
    temporary = 0
    negative = 0
    stat = ""
    percentage = 0
    v = 0
    dv = 0
    dt = to_int("1")
    target_type = ()
    drain_to = ()

    @classmethod
    def interpret(cls, d):
        for k, f in [
            ("duration", to_int),
            ("stack", int),
            ("temporary", int),
            ("negative", int),
            ("stat", str),
            ("percentage", int),
            ("v", to_int),
            ("dv", to_int),
            ("dt", to_int),
        ]:
            if k in d:
                d[k] = f(d[k][0])
        if "dt" in d and d["dt"] < to_int(".1"):
            warning("dt is too small: using .1 instead")
            d["dt"] = to_int(".1")
        if "stat" in d and d["stat"] not in ALLOWED_STATS:
            warning('the "%s" stat might not work well with buffs', d["stat"])
        if "drain_to" in d:
            n = len(d["drain_to"])
            d["drain_to"] = [x for x in d["drain_to"] if x in ["hp", "mana"]]
            if len(d["drain_to"]) != n:
                warning(
                    'drain_to can only contain "hp" and/or "mana", in priority order'
                )

    def __init__(self, author, host):
        self.author = author
        self._time_left = self.duration
        if self.dv:
            self._t = 0
        if self.temporary:
            self._variation = 0
        self._apply_variation(
            host, getattr(host, self.stat) * self.percentage // 100 + self.v
        )
        if author.cls.__name__ == "Item":
            host.notify(
                "buff,add,%s,%s %s%s"
                % (
                    self.type_name,
                    self.stat,
                    "+" if self._variation > 0 else "",
                    str(self._variation / PRECISION),
                )
            )
        else:
            host.notify("buff,add,%s," % self.type_name)

    @property
    def type_name(self):
        return self.__class__.__name__

    def renew(self):
        self._time_left = self.duration

    def _apply_variation(self, host, v):
        initial_value = getattr(host, self.stat)
        if self.negative:
            v *= -1
        if v < 0 and self.stat == "hp":
            host.apply_damage(-v, self.author)
        else:
            setattr(host, self.stat, getattr(host, self.stat) + v)
        if self.stat not in ["hp_regen", "mana_regen"] and getattr(host, self.stat) < 0:
            setattr(host, self.stat, 0)
        elif self.stat in ["hp", "mana"] and getattr(host, self.stat) > getattr(
            host, self.stat + "_max"
        ):
            setattr(host, self.stat, getattr(host, self.stat + "_max"))
        variation = getattr(host, self.stat) - initial_value
        for stat in self.drain_to:
            stat_current = getattr(self.author, stat)
            stat_max = getattr(self.author, stat + "_max")
            if stat_current < stat_max:
                setattr(self.author, stat, min(stat_current - variation, stat_max))
                break
        if self.temporary:
            self._variation += variation

    def should_stop(self):
        return self._time_left <= 0

    def update(self, host):
        self._time_left -= VIRTUAL_TIME_INTERVAL
        if self.dv:
            self._t += VIRTUAL_TIME_INTERVAL
            while self._t >= self.dt:
                self._apply_variation(host, self.dv)
                self._t -= self.dt

    def stop(self, host):
        if self.temporary:
            setattr(host, self.stat, getattr(host, self.stat) - self._variation)
            host.notify("buff,del,%s" % self.type_name)
