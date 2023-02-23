from unittest.mock import Mock

import pytest

from soundrts.definitions import style
from soundrts.lib.nofloat import PRECISION
from soundrts.worldplayerbase import Stats, Player

GOLD = 0
WOOD = 1


@pytest.fixture
def stats():
    stats = Stats(Player(Mock(), Mock()))
    stats.player.resources = [0, 0]
    stats.player.world.time = 15 * PRECISION
    return stats


def test_add_and_get(stats):
    assert stats.get("produced", "unit") == 0
    stats.add("produced", "unit")
    assert stats.get("produced", "unit") == 1

    assert stats.get("gathered", GOLD) == 0
    stats.add("gathered", GOLD, 5)
    assert stats.get("gathered", GOLD) == 5


def test_consumed(stats):
    assert stats.consumed(GOLD) == 0

    stats.add("gathered", GOLD, 5)
    assert stats.consumed(GOLD) == 5  # since no gold left

    stats.player.resources = [5, 0]
    assert stats.consumed(GOLD) == 0


def test_score(stats):
    stats.add("gathered", GOLD, 100 * PRECISION)
    assert stats.score() == 200  # gathered + consumed

    stats.add("produced", "unit")
    assert stats.score() == 201

    stats.add("lost", "unit")
    assert stats.score() == 200

    stats.add("killed", "unit")
    assert stats.score() == 201

    stats.add("produced", "building")
    assert stats.score() == 202

    stats.add("lost", "building")
    assert stats.score() == 201

    stats.add("killed", "building")
    assert stats.score() == 202


STYLE = """
def parameters
resource_0_title 131
resource_1_title 132
"""


def test_score_msgs(stats):
    style.load(STYLE)
    stats.add("gathered", GOLD, 100 * PRECISION)
    stats.add("produced", "unit")
    stats.add("lost", "unit")
    stats.add("killed", "unit")
    stats.add("produced", "building")
    stats.add("lost", "building")
    stats.add("killed", "building")
    stats.freeze()
    stats.player.world.time = 30 * PRECISION  # ignored after freeze

    assert stats.score_msgs() == [[150, 107, 1000000, 65, 1000015, 66],
                                  [1000001, 130, 4023, 9998, 1000001, 146, 9998, 1000001, 145],
                                  [1000001, 4025, 4022, 9998, 1000001, 146, 9998, 1000001, 145],
                                  [1000100, '131', 4256, 9998, 1000100, 4024],
                                  [1000000, '132', 4256, 9998, 1000000, 4024],
                                  [4026, 1000202, 2008]]
