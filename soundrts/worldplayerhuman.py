from worldplayerbase import Player


class Human(Player):

    observer_if_defeated = True

    def __repr__(self):
        return "Human(%s)" % self.client

    is_human = True
