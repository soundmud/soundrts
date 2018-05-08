from soundrts.worldclient import ReplayClient


class Player:
    pass


class ReplayGame:

    record_replay = False

    def replay_read(self):
        if self.lines:
            return self.lines.pop(0)
        return ""


class World:

    time = 0

    def update(self):
        self.time += 300


def test_replay_client_world_update():
    p = Player()
    g = ReplayGame()
    g.lines = ["300 0 order1", "900 0 order2"]
    c = ReplayClient(p, g)
    c.player = p
    p.world = World()
    p.world.players = [p]
    assert c.get_orders() == []
    p.world.update()
    assert c.get_orders() == [(p, "order1")]
    p.world.update()
    assert c.get_orders() == []
    p.world.update()
    assert c.get_orders() == [(p, "order2")]
    p.world.update()
    assert c.get_orders() == []
