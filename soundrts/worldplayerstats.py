from . import msgparts as mp
from soundrts.lib.nofloat import PRECISION
from .definitions import style
from .lib.msgs import nb2msg


class Stats:
    time: int

    def __init__(self, player):
        self._stats = {}
        self.player = player

    def freeze(self):
        self.time = self.player.world.time

    def add(self, event, target, inc=1):
        if target is not None:
            stat = (event, target)
            try:
                self._stats[stat] += inc
            except KeyError:
                self._stats[stat] = inc

    def get(self, event, target):
        return self._stats.get((event, target), 0)

    def consumed(self, i):
        return self.get("gathered", i) - self.player.resources[i]

    def score(self):
        score = 0
        for t in ["unit", "building"]:
            score += self.get("produced", t)
            score -= self.get("lost", t)
            score += self.get("killed", t)
        for i, _ in enumerate(self.player.resources):
            score += (
                             self.get("gathered", i) + self.consumed(i)
                     ) // PRECISION
        return score

    def game_duration_in_minutes_seconds(self):
        t = self.time // 1000
        m = int(t // 60)
        s = int(t - m * 60)
        return m, s

    def score_msgs(self):
        if self.player.has_victory:
            victory_or_defeat = mp.VICTORY
        else:
            victory_or_defeat = mp.DEFEAT
        minutes, seconds = self.game_duration_in_minutes_seconds()
        msgs = [victory_or_defeat + mp.AT + nb2msg(minutes) + mp.MINUTES + nb2msg(seconds) + mp.SECONDS]
        for unit_type, produced_msg in [("unit", mp.UNITS + mp.PRODUCED_F), ("building", mp.BUILDINGS + mp.PRODUCED_M)]:
            msgs.append(
                nb2msg(self.get("produced", unit_type))
                + produced_msg
                + mp.COMMA
                + nb2msg(self.get("lost", unit_type))
                + mp.LOST
                + mp.COMMA
                + nb2msg(self.get("killed", unit_type))
                + mp.NEUTRALIZED
            )
        for i, _ in enumerate(self.player.resources):
            msgs.append(
                nb2msg(self.get("gathered", i) // PRECISION)
                + style.get("parameters", "resource_%s_title" % i)
                + mp.GATHERED
                + mp.COMMA
                + nb2msg(self.consumed(i) // PRECISION)
                + mp.CONSUMED
            )
        msgs.append(mp.SCORE + nb2msg(self.score()) + mp.HISTORY_EXPLANATION)
        return msgs
