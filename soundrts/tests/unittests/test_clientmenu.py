import pygame
import pytest

from soundrts import clientmedia
from soundrts.clientmenu import _first_letter
from soundrts.lib.resource import ResourceStack
from soundrts.lib.sound_cache import sounds
from soundrts.paths import BASE_PACKAGE_PATH


@pytest.fixture(scope="module")
def default(request):
    clientmedia.minimal_init()
    res = ResourceStack([BASE_PACKAGE_PATH])
    request.addfinalizer(pygame.display.quit)
    return res


def test_first_letter(default):
    sounds.load_default(default)
    assert _first_letter([[4031], None]) == sounds.text("4031")[0].lower()
    assert _first_letter([['4267'], None]) == sounds.text("4267")[0].lower()
    assert _first_letter([['orc'], None]) == 'o'
    assert _first_letter([['Orc'], None]) == 'o'
    assert _first_letter([['4267', 'editor'], None]) == sounds.text("4267")[0].lower()
    assert _first_letter([['orc', 'editor'], None]) == 'o'
    assert _first_letter([[1000, 'orc', 'editor'], None]) == 'o'
