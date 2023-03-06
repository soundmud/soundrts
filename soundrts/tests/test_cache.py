import pygame
import pytest

from soundrts import clientmedia
from soundrts.campaign import Campaign
from soundrts.definitions import get_ai, rules, style, load_ai
from soundrts.lib import resource
from soundrts.lib.package import Package
from soundrts.lib.resource import ResourceStack
from soundrts.lib.sound_cache import sounds
from soundrts.mapfile import Map
from soundrts.pack import pack_file_or_folder
from soundrts.paths import BASE_PACKAGE_PATH

maps_paths = ["soundrts/tests/single/map1", "soundrts/tests/single/map1.zip"]
maps = [Map(path) for path in maps_paths]
campaigns = [
    Campaign(Package.from_path("soundrts/tests/single/campaign1"), "campaign1"),
    Campaign(Package.from_path("soundrts/tests/single/campaign1.zip"), "campaign1"),
]

resource.preferred_language = "en"


@pytest.fixture(scope="module")
def default(request):
    clientmedia.minimal_init()
    res = ResourceStack([BASE_PACKAGE_PATH])
    request.addfinalizer(pygame.display.quit)
    return res


@pytest.fixture(scope="module")
def test(request):
    clientmedia.minimal_init()
    res = ResourceStack(["soundrts/tests/res"])
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
    # a sound can be stored in a subdirectory
    assert sounds.get_sound("1028") is not None


def test_text(test):
    res = test
    res.language = "en"
    sounds.load_default(res)
    assert sounds.text("0") == "yes"
    assert sounds.text("1") == "no"
    assert sounds.text("2") is None


def test_text_with_locale(test):
    res = test
    res.language = "fr"
    sounds.load_default(res)
    assert sounds.text("0") == "oui"
    assert sounds.text("1") == "no"
    assert sounds.text("2") is None


def test_get_style(test):
    res = test
    res.language = "en"

    style.load(res.text("ui/style", append=True, localize=True))
    assert style.get("peasant", "test") == ["0"]


def test_get_style_with_locale(test):
    res = test
    res.language = "fr"

    style.load(res.text("ui/style", append=True, localize=True))
    assert style.get("peasant", "test") == ["1"]


def test_get_rules_and_ai(test):
    res = test

    rules.load(res.text("rules", append=True))
    load_ai(res.text("ai", append=True))
    assert rules.get("peasant", "cost") == [0, 0]
    assert rules.get("test", "cost") == [0, 0]
    assert get_ai("easy") == ["get 1 peasant", "goto -1"]


def test_folder_map(test):
    res = test
    res.language = "en"

    for m in maps:
        assert m.name == "map1"
        assert m.definition == "title 11 22\n"
        assert sounds.text("0") != "map1"
        res.set_map(m)
        try:
            assert rules.get("test", "cost") == [0, 0]
            assert rules.get("peasant", "cost") == [6000, 0]
            assert get_ai("easy") == ["get 6 peasant", "goto -1"]
            assert style.get("peasant", "test") == ["6"]
            assert sounds.text("0") == "map1"
            assert set(rules.factions) == {"faction1", "faction2"}
        finally:
            res.set_map()
        assert rules.get("test", "cost") == [0, 0]
        assert rules.get("peasant", "cost") == [0, 0]
        assert get_ai("easy") == ["get 1 peasant", "goto -1"]
        assert style.get("peasant", "test") == ["0"]
        assert sounds.text("0") == "yes"


def test_campaign(test):
    for c in campaigns:
        assert sounds.text("0") == "yes"
        test.set_campaign(c)
        assert sounds.text("0") == "campaign1"
        test.set_campaign()
        assert sounds.text("0") == "yes"


def test_campaign_cutscene(test):
    res = test
    for c in campaigns:
        res.set_campaign(c)
        m = c.chapters[0]
        assert sounds.text("0") == "campaign1"
        res.set_campaign()


def test_campaign_map(test):
    res = test
    for campaign in campaigns:
        res.set_campaign(campaign)
        try:
            chapter = campaign.chapters[2]
            assert chapter.map.name == "campaign1/2"
            assert chapter.title == [11, 22]
            assert chapter.map.resources is None
            res.set_map(chapter.map)
            try:
                assert rules.get("test", "cost") == [0, 0]
                assert rules.get("peasant", "cost") == [5000, 0]
                assert get_ai("easy") == ["get 5 peasant", "goto -1"]
                assert style.get("peasant", "test") == ["5"]
                assert sounds.text("0") == "campaign1"
            finally:
                res.set_map()
        finally:
            res.set_campaign()


def test_campaign_map_with_special_rules(test):
    res = test
    for campaign in campaigns:
        res.set_campaign(campaign)
        chapter = campaign.chapters[1]
        assert chapter.map.name == "campaign1/1"
        res.set_map(chapter.map)
        assert rules.get("test", "cost") == [0, 0]
        assert rules.get("peasant", "cost") == [7000, 0]
        assert get_ai("easy") == ["get 7 peasant", "goto -1"]
        assert style.get("peasant", "test") == ["7"]
        assert sounds.text("0") == "campaign1 map1"
        res.set_map()
        res.set_campaign()


def test_unpacked_folder_map_redefines_resources(test):
    for path in maps_paths:
        default_text = sounds.text("0")
        default_sound = sounds.get_sound("9998")

        m = test.unpack_map(pack_file_or_folder(path))
        test.set_map(m)

        assert sounds.text("0") == "map1"
        assert sounds.text("0") != default_text
        assert isinstance(sounds.get_sound("9998"), pygame.mixer.Sound)
        assert sounds.get_sound("9998").mod_name != default_sound.mod_name
        assert rules.get("test", "cost") == [0, 0]
        assert rules.get("peasant", "cost") == [6000, 0]
        assert get_ai("easy") == ["get 6 peasant", "goto -1"]
        assert style.get("peasant", "test") == ["6"]

        test.set_map()

        assert sounds.text("0") == default_text
        assert sounds.get_sound("9998").mod_name == default_sound.mod_name
