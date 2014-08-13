import pygame

from clientmediascreen import get_screen, draw_line, draw_rect
from lib.log import warning
from nofloat import square_of_distance
from worldunit import Building, BuildingSite


R = int(0.5 * 10)
R2 = R * R


class GridView(object):

    def __init__(self, interface):
        self.interface = interface

    def _display(self):
        # backgrounds
        for xc in range(0, self.interface.xcmax + 1):
            for yc in range(0, self.interface.ycmax + 1):
                sq = self.interface.server.player.world.grid[(xc, yc)]
                x, y = xc * self.square_view_width, self.ymax - yc * self.square_view_height
                if sq in self.interface.server.player.detected_squares:
                    color = (0, 25, 25)
                elif sq in self.interface.server.player.observed_squares:
                    color = (0, 25, 0)
                elif sq in self.interface.server.player.observed_before_squares:
                    color = (15, 15, 15)
                else:
                    color = (0, 0, 0)
                    continue
                if sq.high_ground:
                    color = (color[0]*2, color[1]*2, color[2]*2)
                draw_rect(color, x, y - self.square_view_height, self.square_view_width, self.square_view_height, 0)
        # grid
        color = (100, 100, 100)
        for x in range(0, self.interface.xcmax + 2):
            draw_line(color, (x * self.square_view_width, 0), (x * self.square_view_width, (self.interface.ycmax + 1)* self.square_view_height))
        for y in range(0, self.interface.ycmax + 2):
            draw_line(color, (0, y * self.square_view_height), ((self.interface.xcmax + 1) * self.square_view_width, y * self.square_view_height))

    def active_square_view_display(self):
        xc, yc = self.interface.coords_in_map(self.interface.place)
        x, y = xc * self.square_view_width, self.ymax - yc * self.square_view_height
        if self.interface.target is None:
            color = (255, 255, 255)
        else:
            color = (150, 150, 150)
        draw_rect(color, x, y - self.square_view_height, self.square_view_width, self.square_view_height, 1)

    def object_coords(self, o):
        x = int(o.x / self.interface.square_width * self.square_view_width)
        y = int(self.ymax - o.y / self.interface.square_width * self.square_view_height)
        return (x, y)

    def xy_coords(self, ox, oy):
        ox /= 1000.0
        oy /= 1000.0
        x = int(ox / self.interface.square_width * self.square_view_width)
        y = int(self.ymax - oy / self.interface.square_width * self.square_view_height)
        return x, y

    def display_object(self, o):
        if getattr(o, "is_inside", False):
            return
        if self.interface.target is not None and self.interface.target is o:
            width = 0 # fill circle
        else:
            width = 1
        x, y = self.object_coords(o)
        if isinstance(o.model, (Building, BuildingSite)):
            draw_rect(o.corrected_color(), x-R, y-R, R*2, R*2, width)
        else:
            pygame.draw.circle(get_screen(), o.corrected_color(), (x, y), R, width)
        if getattr(o.model, "player", None) is not None:
            if o.id in self.interface.group:
                color = (0,255,0)
            elif o.player is self.interface.player:
                color = (0,55,0)
            elif o.player in self.interface.player.allied:
                color = (0,0,155)
            elif o.player.is_an_enemy(self.interface.player):
                color = (155,0,0)
            else:
                color = (0, 0, 0)
            pygame.draw.circle(get_screen(), color, (x, y), R/2, 0)
            if getattr(o, "hp", None) is not None and \
               o.hp != o.hp_max:
                hp_prop = 100 * o.hp / o.hp_max
                if hp_prop > 80:
                    color = (0, 255, 0)
##                elif hp_prop > 50:
##                    color = (0, 255, 0)
                else:
                    color = (255, 0, 0)
                W = R - 2
                if color != (0, 255, 0):
                    pygame.draw.line(get_screen(), (0, 55, 0),
                                 (x - W, y - R - 2),
                                 (x - W + 2 * W, y - R - 2))
                pygame.draw.line(get_screen(), color,
                                 (x - W, y - R - 2),
                                 (x - W + hp_prop * (2 * W) / 100, y - R - 2))

    def display_objects(self):
        for o in self.interface.dobjets.values():
            self.display_object(o)
            if o.place is None and not o.is_inside \
               and not (self.interface.already_asked_to_quit or
                        self.interface.end_loop):
                warning("%s.place is None", o.type_name)
                if o.is_memory:
                    warning("(memory)")

    def _update_coefs(self):
        self.square_view_width = self.square_view_height = min((get_screen().get_width() - 200) / (self.interface.xcmax + 1),
            get_screen().get_height() / (self.interface.ycmax + 1)) # 200 = graphic console
        self.ymax = self.square_view_height * (self.interface.ycmax + 1)

    def _collision_display(self):
        for t, c in (("ground", (0, 0, 255)), ("air", (255, 0, 0))):
            for ox, oy in self.interface.collision_debug[t].xy_set():
                pygame.draw.circle(get_screen(), c, self.xy_coords(ox, oy), 0, 0)

    def display(self):
        self._update_coefs()
        self._display()
        self.display_objects()
        if self.interface.zoom_mode:
            self.interface.zoom.display(self)
        else:
            self.active_square_view_display()
        if self.interface.collision_debug:
            self._collision_display()

    def square_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        xc = x / self.square_view_width
        yc = (self.ymax - y) / self.square_view_height
        if 0 <= xc <= self.interface.xcmax and 0 <= yc <= self.interface.ycmax:
            return self.interface.server.player.world.grid[(xc, yc)]

    def object_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        for o in self.interface.dobjets.values():
            xo, yo = self.object_coords(o)
            if square_of_distance(x, y, xo, yo) <= R2 + 1: # XXX + 1 ?
                return o

    def units_from_mouserect(self, pos, pos2):
        result= []
        self._update_coefs()
        x, y = pos
        x2, y2 = pos2
        if x > x2: x, x2 = x2, x
        if y > y2: y, y2 = y2, y
        for o in self.interface.units():
            xo, yo = self.object_coords(o)
            if x < xo < x2 and y < yo < y2:
                result.append(o.id)
        return result

    def display_attack(self, attacker_id, target):
        a = self.interface.dobjets[attacker_id]
        self.interface.grid_view._update_coefs()
        if self.interface.player.is_an_enemy(a):
            color = (255, 0, 0)
        else:
            color = (0, 255, 0)
        pygame.draw.line(get_screen(), color,
                         self.interface.grid_view.object_coords(target),
                         self.interface.grid_view.object_coords(a))
        pygame.draw.circle(get_screen(), (100, 100, 100),
                           self.interface.grid_view.object_coords(target), R*3/2, 0)
        pygame.display.flip() # not very clean but seems to work (persistence of vision?)
        # better: interface.anims queue to render when the time has come
        # (not during the world model update)
