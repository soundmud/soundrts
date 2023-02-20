from soundrts.definitions import Rules, Style


def _example_rules():
    rules = Rules()
    rules.load("def number\nclass int", classes={"int": int})
    return rules


def test_load_rules():
    rules = _example_rules()
    number_class = rules.classes["number"]
    assert issubclass(number_class, int)


def test_copy_rules():
    rules = Rules()
    rules.copy(_example_rules())
    assert "number" in rules.classes


def _example_style():
    style = Style()
    style.load("def thing\ntitle 1")
    return style


def test_load_style():
    style = _example_style()
    assert style.get("thing", "title") == ["1"]


def test_copy_style():
    style = Style()
    style.copy(_example_style())
    assert style.has("thing", "title")
