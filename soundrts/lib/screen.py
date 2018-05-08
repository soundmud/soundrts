import ctypes

import pygame
from pygame.locals import FULLSCREEN

from .log import warning


pygame.font.init()
_font = pygame.font.Font("freesansbold.ttf", 12)

def draw_line(color, xy1, xy2):
    pygame.draw.line(_screen, color, xy1, xy2)

def draw_rect(color, rect, width2=0):
    pygame.draw.rect(_screen, color, pygame.Rect(*rect), width2)

def _get_desktop_screen_mode():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except:
        if pygame.display.get_init():
            warning("Info() must be called before set_mode()")
        pygame.display.init()
        i = pygame.display.Info()
        try:
            return i.current_w, i.current_h
        except:
            return 640, 480

def get_desktop_screen_mode():
    return _x, _y

def screen_render(text, dest, right=False, center=False, color=(200, 200, 200)):
    surface = _font.render(text, True, color, (0, 0, 0))
    r = surface.get_rect()
    if right:
        if dest[0] == -1:
            dest = list(dest)
            dest[0] += pygame.display.get_surface().get_width()
        r.right, r.top = dest
    elif center:
        r.center = dest
    else:
        r = dest
    _screen.blit(surface, r)

def screen_render_subtitle():
    ren = _font.render(_subtitle, True, (200, 200, 200), (0, 0, 0))
    x = (_screen.get_width() - ren.get_width()) / 2
    y = _screen.get_height() - ren.get_height()
    _screen.blit(ren, (x, y))

def screen_subtitle_set(txt):
    global _subtitle
    if _game_mode:
        # render later
        _subtitle = txt
    else:
        get_screen().fill((0, 0, 0))
        screen_render(txt, (0, 0))
        pygame.display.flip()

def set_game_mode(m):
    global _game_mode
    _game_mode = m

def set_screen(fullscreen):
    global _screen
    if fullscreen:
        x, y = get_desktop_screen_mode()
        window_style = 0 | FULLSCREEN
    else:
        x, y = 400, 75
        window_style = 0
        pygame.mouse.set_visible(True)
    try:
        _screen = pygame.display.set_mode((x, y), window_style)
    except:
        _screen = pygame.display.set_mode((640, 480))

def get_screen():
    return _screen

_x, _y = _get_desktop_screen_mode()
_screen = None
_game_mode = False
_subtitle = ""
