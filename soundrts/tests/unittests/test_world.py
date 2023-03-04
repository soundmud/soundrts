from soundrts.lib.nofloat import to_int
from soundrts.world import convert_and_split_first_numbers


def test_convert_and_split_first_numbers():
    f = convert_and_split_first_numbers
    assert f(["1", "9", "a1", "2", "peasant"]) == ([to_int("1"), to_int("9")], ["a1", "2", "peasant"])
    assert f(["1", "9", "a1"]) == ([to_int("1"), to_int("9")], ["a1"])
    assert f(["1", "a1"]) == ([to_int("1")], ["a1"])
    assert f(["a1"]) == ([], ["a1"])
    assert f([]) == ([], [])
    assert f(["a1", "2", "peasant"]) == ([], ["a1", "2", "peasant"])
    assert f(["1", "9"]) == ([to_int("1"), to_int("9")], [])
