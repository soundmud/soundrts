from soundrts.lib.resource import localize_path, best_language_match


def test_localize_path():
    assert localize_path("/ui", "fr").replace("\\", "/") == "/ui-fr"
    assert localize_path("/ui/", "fr").replace("\\", "/") == "/ui-fr/"
    assert localize_path("/uii", "fr").replace("\\", "/") == "/uii"
    assert localize_path("/oui", "fr").replace("\\", "/") == "/oui"
    assert localize_path("/ui/i", "fr").replace("\\", "/") == "/ui-fr/i"
    assert localize_path("/ui/io/i", "fr").replace("\\", "/") == "/ui/io/i"
    assert localize_path("/oui/i", "fr").replace("\\", "/") == "/oui/i"


def test_best_language_match():
    AVAILABLE_LANGUAGES = ['en', 'cs', 'de', 'es', 'fr', 'it', 'pl', 'pt-BR', 'ru', 'sk', 'zh']
    assert best_language_match("en", AVAILABLE_LANGUAGES) == "en"
    assert best_language_match("fr_ca", AVAILABLE_LANGUAGES) == "fr"
    assert best_language_match("fr", AVAILABLE_LANGUAGES) == "fr"
    assert best_language_match("pt_BR", AVAILABLE_LANGUAGES) == "pt-BR"
    assert best_language_match("pt_br", AVAILABLE_LANGUAGES) == "pt-BR"
    assert best_language_match("pt", AVAILABLE_LANGUAGES) == "pt-BR"
    assert best_language_match("de", AVAILABLE_LANGUAGES) == "de"
    assert best_language_match("pl", AVAILABLE_LANGUAGES) == "pl"
    assert best_language_match("es", AVAILABLE_LANGUAGES) == "es"
