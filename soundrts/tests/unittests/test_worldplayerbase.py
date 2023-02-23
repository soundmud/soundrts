from unittest.mock import Mock

from soundrts.worldplayerhuman import Human


def test_on_unit_attacked():
    player = Human(Mock(), Mock())
    unit = Mock()
    player.units = [unit]
    hostile_unit = Mock()
    player.perception.add(hostile_unit)

    player.on_unit_attacked(unit, hostile_unit)

    assert hostile_unit.place in player._counterattack_places


def _counterattacks_setup(unit_nearby=True):
    player = Human(Mock(), Mock())
    unit = Mock()
    player.units = [unit]
    attacker_place = Mock()
    attacker_place.neighbors = [unit.place] if unit_nearby else []
    player._counterattack_places = [attacker_place]
    return player, unit


def test_update_counterattacks():
    player, unit = _counterattacks_setup()

    player._update_counterattacks()

    assert player._counterattack_places == []
    unit.counterattack.assert_called_once()


def test_update_counterattacks_if_not_nearby():
    player, unit = _counterattacks_setup(unit_nearby=False)

    player._update_counterattacks()

    assert player._counterattack_places == []
    unit.counterattack.assert_not_called()


def test_update_counterattacks_if_closer_attackers():
    player, unit = _counterattacks_setup()
    player._counterattack_places += [unit.place]
    unit.place.neighbors = []

    player._update_counterattacks()

    assert player._counterattack_places == []
    unit.counterattack.assert_not_called()
