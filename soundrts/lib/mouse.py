import pygame

my_cursors = {}


def record_cursor(name, center, strings):
    data, mask = pygame.cursors.compile(strings)
    my_cursors[name] = ((len(strings),) * 2, center, data, mask)


record_cursor(
    "square",
    (4, 4),
    (
        "XXXXXXXX",
        "X      X",
        "X      X",
        "X      X",
        "X      X",
        "X      X",
        "X      X",
        "XXXXXXXX",
    ),
)

record_cursor(
    "target",
    (4, 4),
    (
        "  XXXX  ",
        " X    X ",
        "X      X",
        "X  XX  X",
        "X  XX  X",
        "X      X",
        " X    X ",
        "  XXXX  ",
    ),
)


def set_cursor(name):
    if name in my_cursors:
        cursor = my_cursors[name]
    else:
        cursor = getattr(pygame.cursors, name)
    pygame.mouse.set_cursor(*cursor)
