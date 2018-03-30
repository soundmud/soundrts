from lib import group
from lib.log import exception
import msgparts as mp
from worldplayerbase import Player


class Human(Player):

    observer_if_defeated = True

    def __init__(self, world, client):
        self.name = client.login
        Player.__init__(self, world, client)

    def __repr__(self):
        return "<Human>"

    def is_human(self):
        return True

    def _reset_group(self, name):
        if name in self.groups:
            for u in self.groups[name]:
                u.group = None
            self.groups[name] = []

    def cmd_order(self, args):
        self.group_had_enough_mana = False
        try:
            order_id = self.world.get_next_order_id() # used when several workers must create the same construction site
            forget_previous = args[0] == "0"
            del args[0]
            imperative = args[0] == "1"
            del args[0]
            if args[0] == "reset_group":
                self._reset_group(args[1])
                return
            for u in self.group:
                if u.group and u.group != self.group:
                    u.group.remove(u)
                    u.group = None
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

    def cmd_update(self, unused_args):
        self.ready = True
        self.update_eventuel()

    def cmd_say(self, args):
        msg = [self.client.login] + mp.SAYS + [" ".join(args)]
        self.broadcast_to_others_only(msg)
