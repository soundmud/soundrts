from soundrts.lib.resource import ResourceStack, localized_paths, res, official_multiplayer_maps
from soundrts.lib.resource import best_language_match, localized_path


def test_localize_path():
    assert localized_path("/ui", "fr").replace("\\", "/") == "/ui-fr"
    assert localized_path("/ui/", "fr").replace("\\", "/") == "/ui-fr/"
    assert localized_path("/uii", "fr").replace("\\", "/") == "/uii"
    assert localized_path("/oui", "fr").replace("\\", "/") == "/oui"
    assert localized_path("/ui/i", "fr").replace("\\", "/") == "/ui-fr/i"
    # Is this test useful? I'm not sure.
    #    assert localize_path("/ui/io/i", "fr").replace("\\", "/") == "/ui/io/i"
    assert localized_path("/oui/i", "fr").replace("\\", "/") == "/oui/i"


def test_best_language_match():
    available = ["en", "cs", "de", "es", "fr", "it", "pl", "pt-BR", "ru", "sk", "zh"]
    assert best_language_match("en", available) == "en"
    assert best_language_match("fr_ca", available) == "fr"
    assert best_language_match("fr", available) == "fr"
    assert best_language_match("pt_BR", available) == "pt-BR"
    assert best_language_match("pt_br", available) == "pt-BR"
    assert best_language_match("pt", available) == "pt-BR"
    assert best_language_match("de", available) == "de"
    assert best_language_match("pl", available) == "pl"
    assert best_language_match("es", available) == "es"


def _mods(_packages):
    return [(p.name, p.__class__.__name__) for p in _packages]


def test_update():
    assert localized_path("ui", "en") == "ui-en"
    assert localized_paths("ui", "en") == ["ui", "ui-en"]

    r = ResourceStack(["soundrts/tests/res", "soundrts/tests/res2"])
    assert _mods(r._layers) == [("default", "FolderPackage")]
    assert r.mods == ""
    assert r.soundpacks == ""
    assert r.text("rules") == 'def test\ncost 0 0\n\ndef peasant\ncost 0 0\n'

    r = ResourceStack(["soundrts/tests/res.zip", "soundrts/tests/res2"])
    assert _mods(r._layers) == [("default", "ZipPackage")]
    assert r.mods == ""
    assert r.soundpacks == ""
    assert r.text("rules") == 'def test\ncost 0 0\n\ndef peasant\ncost 0 0\n'

    r = ResourceStack(["soundrts/tests/res.zip"])
    r.set_mods("mod1,mod2")
    r.set_soundpacks("sound1")
    assert _mods(r._layers) == [("default", "ZipPackage")]
    assert r.mods == ""
    assert r.soundpacks == ""

    r = ResourceStack(["soundrts/tests/res.zip", "soundrts/tests/res2"])
    r.set_mods("mod1,mod2")
    r.set_soundpacks("sound1")
    assert _mods(r._layers) == [("default", "ZipPackage"),
                                ("mod1", "FolderPackage"), ("mod2", "FolderPackage"),
                                ("sound1", "FolderPackage")]
    assert r.mods == "mod1,mod2"
    assert r.soundpacks == "sound1"

    r = ResourceStack(["soundrts/tests/res.zip", "soundrts/tests/res2.zip"])
    r.set_mods("mod,mod2")
    assert _mods(r._layers) == [("default", "ZipPackage"), ("mod2", "ZipPackage")]
    assert r.mods == "mod2"
    assert r.soundpacks == ""


def test_maps_list():
    assert res.multiplayer_maps()
    assert official_multiplayer_maps()
