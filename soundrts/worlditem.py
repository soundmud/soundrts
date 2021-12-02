from soundrts.worldentity import Entity


class Item(Entity):
    default_order = "pickup"
    abilities = ()
    buffs = ()
    # aura_buffs = ()
    # attack_buffs = ()
    is_loot = 0

    @classmethod
    def interpret(cls, d):
        for k, f in [
            ("is_loot", int),
        ]:
            if k in d:
                d[k] = f(d[k][0])

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._buffs = []

    def equip(self, host):
        for a in self.abilities:
            host.can_use = list(host.can_use) + [a]
        for b in self.buffs:
            cls = host.world.unit_class(b)
            self._buffs.append(cls(self, host))

    def unequip(self, host):
        for a in self.abilities:
            host.can_use.remove(a)
        for b in self._buffs:
            b.stop(host)
        self._buffs = []

    def update_in_inventory(self, host):
        for b in self._buffs:
            b.update(host)
