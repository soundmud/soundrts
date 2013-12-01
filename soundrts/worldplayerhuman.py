from worldplayerbase import *


class Human(Player):

    def update_attack_squares(self, unit):
        pass

    def __init__(self, world, client):
        self.name = client.login
        Player.__init__(self, world, client)

    def on_unit_attacked(self, unit, attacker=None):
        pass

    def on_target_destroyed(self, unit):
        pass

    def send_alert(self, square, sound):
        self.push("alert %s,%s\n" % (square.id, sound))

    def is_human(self):
	return True

    @property
    def allied_control_units(self):
        result = []
        for p in self.allied_control:
            result.extend(p.units)
        return result

    def cmd_order(self, args):
        self.group_had_enough_mana = False
        try:
            order_id = self.world.get_next_order_id() # used when several workers must create the same construction site
            forget_previous = args[0] == "0"
            del args[0]
            imperative = args[0] == "1"
            del args[0]
            for u in self.group:
                if u.player in self.allied_control: # in case the unit has died or has been converted
                    try:
                        if args[0] == "default":
                            u.take_default_order(args[1], forget_previous, imperative, order_id)
                        else:
                            u.take_order(args, forget_previous, imperative, order_id)
                    except:
                        exception("problem with order: %s" % args)
        except:
            exception("problem with order: %s" % args)

    def cmd_control(self, args):
        self.group = []
        for obj_id in group.decode(" ".join(args)):
            for u in self.allied_control_units:
                if u.id == obj_id:
                    self.group.append(u)
                    break

    def _is_admin(self):
        return self.client == self.world.admin

    def cmd_speed(self, args):
        if self._is_admin():
            for p in self.world.players:
                p.push("speed %s\n" % float(args[0]))
        else:
            warning("non admin client tried to change game speed")

    def cmd_update(self, unused_args):
        self.ready = True
        self.update_eventuel()

##    def cmd_restore(self, args):
##        self.disparaitre(True)
##        self.client.cmd_restore(args)

    def cmd_quit(self, unused_args):
        self.defeat()
