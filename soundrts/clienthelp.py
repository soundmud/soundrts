from . import res


def _read_table_from_file(name):
    return [x.split() for x in res.get_text_file(name).split("\n") if x.strip()]

_game_table = _read_table_from_file("ui/game_help")
_menu_table = _read_table_from_file("ui/menu_help")

_previous_context = ""
_index = -1

def help_msg(context="game", incr=1):
    global _index, _previous_context
    if context != _previous_context:
        _index = -1
        _previous_context = context
    if context == "game":
        t = _game_table
    else:
        t = _menu_table
    _index += incr
    if _index >= len(t):
        _index = 0
    if _index < 0:
        _index = len(t) - 1
    return t[_index]
