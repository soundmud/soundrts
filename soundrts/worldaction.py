class Action:
    
    def __init__(self, unit, target):
        self.unit = unit
        self.target = target

    def complete(self):
        self.unit.walked = []
        self.unit.action = None
        self.unit._flee_or_fight_if_enemy()

    def update(self):
        pass


class MoveAction(Action):
    
    def update(self):
        if hasattr(self.target, "other_side"):
            # move towards the center of the next square
            self.unit.walk_to_xy(self.target.other_side.place.x, self.target.other_side.place.y) 
        elif getattr(self.target, "place", None) is self.unit.place:
            self.unit.action_reach_and_use()
        elif self.unit.airground_type == "air":
            self.unit.action_fly_to_remote_target()
        else:
            self.complete()


class MoveXYAction(Action):

    timer = 15 # 5 seconds # XXXXXXXX not beautiful

    def update(self):
        if self.timer > 0:
            self.timer -= 1
            x, y = self.target
            if self.unit.walk_to_xy(x, y):
                self.complete()
        else:
            self.complete()


class AttackAction(Action):

    def update(self): # without moving to another square
        if self.unit.range and self.target in self.unit.place.objects:
            self.unit.action_reach_and_use()
        elif self.unit.is_ballistic and self.unit.place.is_near(getattr(self.target, "place", None)) \
             and self.unit.height > self.target.height:
            self.unit.aim(self.target)
        elif self.unit.special_range and self.unit.place.is_near(getattr(self.target, "place", None)):
            self.unit.aim(self.target)
        else:
            self.complete()
