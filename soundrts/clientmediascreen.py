import ctypes
import StringIO
import textwrap

import pygame

from lib.log import *

import g


pygame.font.init()
FONT = pygame.font.Font("freesansbold.ttf", 12)

def draw_line(color, xy1, xy2):
    pygame.draw.line(g.screen, color, xy1, xy2)

def draw_rect(color, left, top, width, height, width2):
    pygame.draw.rect(g.screen, color, pygame.Rect(left, top, width, height),
                     width2)

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


class GraphicConsole(StringIO.StringIO):

    cursor = 0

    def __init__(self):
        self.buffer = ""
        self.height = get_desktop_screen_mode()[1]
        self.text_screen = pygame.Surface((200, self.height))
        StringIO.StringIO.__init__(self)

    def _write_line(self, text):
        ren = FONT.render(text, True, (200, 200, 200), (0, 0, 0))
        self.text_screen.blit(ren, (0, 20 * self.cursor))
        if self.cursor >= self.height / 20 - 2:
            self.text_screen.blit(self.text_screen, (0, -20))
        else:
            self.cursor += 1

    def write(self, s):
        self.buffer += s
        if (self.buffer != "") and (self.buffer[-1] == "\n"):
            for text in textwrap.wrap(self.buffer, 40):
                self._write_line(text)
            self.buffer = ""

    def display(self):
        g.screen.blit(self.text_screen, (g.screen.get_width() - 200, 0))


_x, _y = _get_desktop_screen_mode()
