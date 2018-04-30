import pygame
import pytest

from soundrts.lib.sound_cache import sounds
from soundrts.lib.resource import ResourceLoader
from soundrts import clientmedia


@pytest.fixture(scope="module")
def default(request):
    clientmedia.minimal_init()
    res = ResourceLoader("", "", [])
    request.addfinalizer(pygame.display.quit)
    return res


@pytest.fixture(scope="module")
def test(request):
    clientmedia.minimal_init()
    res = ResourceLoader("", "", [], base_path="soundrts/tests/res")
    request.addfinalizer(pygame.display.quit)
    return res


def test_get_sound_with_default_config(default):
    # this test is a bit long (it loads all the default sounds)
    res = default
    res.language = "fr"
    sounds.load_default(res)
    assert sounds.get_sound("9999") is not None
    assert sounds.get_sound("fdsgedtgf") is None


def test_get_sound(test):
    res = test
    res.language = "en"
    sounds.load_default(res)
    assert sounds.get_sound("1000") is None
    assert sounds.get_sound("fdsgedtgf") is None
    assert sounds.get_sound("9998") is not None
    assert sounds.get_sound("9999") is None
    assert sounds.get_sound("1028") is None


def test_get_sound_with_locale(test):
    res = test
    res.language = "fr"
    sounds.load_default(res)
    assert sounds.get_sound("1000") is None
    assert sounds.get_sound("fdsgedtgf") is None
    assert sounds.get_sound("9998") is not None
    assert sounds.get_sound("9999") is not None
    # a sound can be stored in a sub directory
    assert sounds.get_sound("1028") is not None


def test_get_text(test):
    res = test
    res.language = "en"
    sounds.load_default(res)
    assert sounds.get_text("0") == "yes"
    assert sounds.get_text("1") == "no"
    assert sounds.get_text("2") is None


def test_get_text_with_locale(test):
    res = test
    res.language = "fr"
    sounds.load_default(res)
    assert sounds.get_text("0") == "oui"
    assert sounds.get_text("1") == "no"
    assert sounds.get_text("2") is None


def test_get_style(test):
    res = test
    res.language = "en"
    from soundrts.definitions import style
    style.load(res.get_text_file("ui/style", append=True, localize=True))
    assert style.get("peasant", "noise") == ["0"]


def test_get_style_with_locale(test):
    res = test
    res.language = "fr"
    from soundrts.definitions import style
    style.load(res.get_text_file("ui/style", append=True, localize=True))
    assert style.get("peasant", "noise") == ["1"]


def test_get_rules_and_ai(test):
    res = test
    from soundrts.definitions import rules, load_ai, get_ai
    rules.load(res.get_text_file("rules", append=True))
    load_ai(res.get_text_file("ai", append=True))
    assert rules.get("peasant", "cost") == [0, 0]
    assert rules.get("test", "cost") == [0, 0]
    assert get_ai("easy") == ['get 1 peasant', 'goto -1']


def test_isolated_map(test):
    res = test
    from soundrts.mapfile import Map
    from soundrts.definitions import rules, get_ai, style
    map1 = Map("soundrts/tests/single/map1")
    map1.load_resources()
    map1.load_rules_and_ai(res)
    map1.load_style(res)
    assert rules.get("test", "cost") == [0, 0]
    assert rules.get("peasant", "cost") == [6000, 0]
    assert get_ai("easy") == ['get 6 peasant', 'goto -1']
    assert style.get("peasant", "noise") == ["6"]
    assert sounds.get_text("0") == "map1"
    map1.unload_resources()


def test_campaign(test):
    from soundrts.campaign import Campaign
    c = Campaign("soundrts/tests/single/campaign1")
    c.load_resources()
    assert sounds.get_text("0") == "campaign1"
    c.unload_resources()


def test_campaign_map(test):
    res = test
    from soundrts.campaign import Campaign
    from soundrts.definitions import rules, get_ai, style
    c = Campaign("soundrts/tests/single/campaign1")
    c.load_resources()
    map0 = c.chapters[0]
    map0.load_resources()
    map0.load_rules_and_ai(res)
    map0.load_style(res)
    assert rules.get("test", "cost") == [0, 0]
    assert rules.get("peasant", "cost") == [5000, 0]
    assert get_ai("easy") == ['get 5 peasant', 'goto -1']
    assert style.get("peasant", "noise") == ["5"]
    assert sounds.get_text("0") == "campaign1"
    map0.unload_resources()
    c.unload_resources()

def test_campaign_map_with_special_rules(test):
    res = test
    from soundrts.campaign import Campaign
    from soundrts.definitions import rules, get_ai, style
    c = Campaign("soundrts/tests/single/campaign1")
    c.load_resources()
    map1 = c.chapters[1]
    map1.load_resources()
    map1.load_rules_and_ai(res)
    map1.load_style(res)
    assert rules.get("test", "cost") == [0, 0]
    assert rules.get("peasant", "cost") == [7000, 0]
    assert get_ai("easy") == ['get 7 peasant', 'goto -1']
    assert style.get("peasant", "noise") == ["7"]
    assert sounds.get_text("0") == "campaign1 map1"
    map1.unload_resources()
    c.unload_resources()
