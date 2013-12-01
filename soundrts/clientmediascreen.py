import StringIO
import textwrap

import pygame

import g

pygame.font.init()
FONT = pygame.font.Font("freesansbold.ttf", 12)

def draw_line(color, xy1, xy2):
    pygame.draw.line(g.screen, color, xy1, xy2)

def draw_rect(color, left, top, width, height, width2):
    pygame.draw.rect(g.screen, color, pygame.Rect(left, top, width, height),
                     width2)

def get_desktop_screen_mode():
    try:
        # get the biggest fullscreen resolution
        # note: sorting is required by pygame 1.7.1 only
        x, y = sorted(pygame.display.list_modes())[-1]
    except:
        x, y = 640, 480
    return x, y


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
