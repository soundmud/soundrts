from math import cos, radians, sin

import pygame

from .definitions import style
from .lib.log import warning
from .lib.nofloat import PRECISION, square_of_distance
from .lib.screen import draw_line, draw_rect, get_screen
from .worldentity import COLLISION_RADIUS


def terrain_color(terrain: str):
    color = style.get(terrain, "color", warn_if_not_found=False)
    try:
        color = pygame.Color(color[0])
    except (IndexError, TypeError,):
        color = (0, 25, 0)
    return color


def intensify(color):
    color = (color[0] * 2, color[1] * 2, color[2] * 2)
    color = tuple(min(x, 255) for x in color)
    return color


def square_color(square):
    color = terrain_color(square.type_name)
    if square.high_ground:
        color = intensify(color)
    return color


def fade(color):
    color = (color[0] / 10 + 15, color[1] / 10 + 15, color[2] / 10 + 15)
    return color


class GridView:
    def __init__(self, interface):
        self.interface = interface

    def _get_rect_from_map_coords(self, xc, yc):
        width, height = self.square_view_width, self.square_view_height
        left, top = xc * width, self.ymax - (yc + 1) * height
        return left, top, width, height

    def _display(self):
        # map borders
        draw_rect(
            (100, 100, 100),
            (
                0,
                0,
                self.square_view_width * (self.interface.xcmax + 1),
                self.square_view_height * (self.interface.ycmax + 1),
            ),
            1,
        )
        # backgrounds
        squares_to_view = []
        player = self.interface.player
        for xc in range(0, self.interface.xcmax + 1):
            for yc in range(0, self.interface.ycmax + 1):
                sq = player.world.grid[(xc, yc)]
                if sq in player.observed_squares or sq in player.observed_before_squares:
                    color = square_color(sq)
                    if sq not in player.observed_squares:
                        color = fade(color)
                    draw_rect(color, self._get_rect_from_map_coords(xc, yc))
                    squares_to_view.append(sq)
        # walls
        for sq in squares_to_view:
            exits = {e.o for e in sq.exits if not e.is_blocked()}
            walls = {-90, 90, 180, 0} - exits
            x, y = self._xy_coords(sq.x, sq.y)
            for color, borders in (((0, 0, 0), walls),):
                for o in borders:
                    dx = cos(radians(o)) * self.square_view_width / 2
                    dy = -sin(radians(o)) * self.square_view_width / 2
                    draw_line(
                        color, (x - dx - dy, y - dy - dx), (x - dx + dy, y - dy + dx)
                    )

    def _get_view_coords_from_world_coords(self, ox, oy):
        x = int(ox / self.interface.square_width * self.square_view_width)
        y = int(self.ymax - oy / self.interface.square_width * self.square_view_height)
        return x, y

    def _object_coords(self, o):
        return self._get_view_coords_from_world_coords(o.x, o.y)

    def _xy_coords(self, ox, oy):
        return self._get_view_coords_from_world_coords(ox / 1000.0, oy / 1000.0)

    def display_object(self, o):
        if getattr(o, "is_inside", False):
            return
        if self.interface.target is not None and self.interface.target is o:
            width = 0  # fill circle
        else:
            width = 1
        x, y = self._object_coords(o)
        if o.shape() == "square":
            rect = x - R, y - R, R * 2, R * 2
            draw_rect(o.corrected_color(), rect, width)
        else:
            if o.collision:
                pygame.draw.circle(get_screen(), o.corrected_color(), (x, y), R, width)
            elif self.interface.target is not None and self.interface.target is o:
                pygame.draw.circle(get_screen(), o.corrected_color(), (x, y), R, 0)
            else:
                get_screen().set_at((x, y), o.corrected_color())
        if getattr(o.model, "player", None) is not None:
            if o.id in self.interface.group:
                color = (0, 255, 0)
            elif o.player is self.interface.player:
                color = (0, 55, 0)
            elif o.player in self.interface.player.allied:
                color = (0, 0, 155)
            elif o.player.player_is_an_enemy(self.interface.player):
                color = (155, 0, 0)
            else:
                color = (0, 0, 0)
            pygame.draw.circle(get_screen(), color, (x, y), R // 2, 0)
            if getattr(o, "hp", None) is not None and o.hp != o.hp_max:
                hp_prop = 100 * o.hp // o.hp_max
                if hp_prop > 80:
                    color = (0, 255, 0)
                else:
                    color = (255, 0, 0)
                W = R - 2
                if color != (0, 255, 0):
                    pygame.draw.line(
                        get_screen(),
                        (0, 55, 0),
                        (x - W, y - R - 2),
                        (x - W + 2 * W, y - R - 2),
                    )
                pygame.draw.line(
                    get_screen(),
                    color,
                    (x - W, y - R - 2),
                    (x - W + hp_prop * (2 * W) // 100, y - R - 2),
                )

    def display_objects(self):
        for o in list(self.interface.dobjets.values()):
            self.display_object(o)
            if (
                o.place is None
                and not o.is_inside
                and not (
                    self.interface.already_asked_to_quit or self.interface.end_loop
                )
            ):
                warning("%s.place is None", o.type_name)
                if o.is_memory:
                    warning("(memory)")

    def _update_coefs(self):
        global R, R2
        self.square_view_width = self.square_view_height = min(
            get_screen().get_width() // (self.interface.xcmax + 1),
            get_screen().get_height() // (self.interface.ycmax + 1),
        )
        self.ymax = self.square_view_height * (self.interface.ycmax + 1)
        R = max(
            1,
            int(
                COLLISION_RADIUS
                / PRECISION
                / self.interface.square_width
                * self.square_view_width
            ),
        )
        R2 = R * R

    def _collision_display(self):
        for t, c in (("ground", (0, 0, 255)), ("air", (255, 0, 0))):
            for ox, oy in self.interface.collision_debug[t].xy_set():
                pygame.draw.circle(get_screen(), c, self._xy_coords(ox, oy), 0, 0)

    def _display_active_zone_border(self):
        if self.interface.zoom_mode:
            zoom = self.interface.zoom
            left, bottom = self._xy_coords(zoom.xmin, zoom.ymin)
            right, top = self._xy_coords(zoom.xmax, zoom.ymax)
            rect = left, top, right - left, bottom - top
        else:
            rect = self._get_rect_from_map_coords(
                *self.interface.coords_in_map(self.interface.place)
            )
            rect = list(rect)
        if self.interface.target is None:
            color = (255, 255, 255)
        else:
            color = (150, 150, 150)
        draw_rect(color, rect, 1)

        # display the observer
        observer_coordinates = self._get_view_coords_from_world_coords(self.interface.x, self.interface.y)
        pygame.draw.circle(get_screen(), color, observer_coordinates, 1, 1)

    def display(self):
        self._update_coefs()
        self._display()
        self.display_objects()
        self._display_active_zone_border()
        if self.interface.collision_debug:
            self._collision_display()

    def square_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        xc = x // self.square_view_width
        yc = (self.ymax - y) // self.square_view_height
        if 0 <= xc <= self.interface.xcmax and 0 <= yc <= self.interface.ycmax:
            return self.interface.server.player.world.grid[(xc, yc)]

    def object_from_mousepos(self, pos):
        self._update_coefs()
        x, y = pos
        for o in list(self.interface.dobjets.values()):
            xo, yo = self._object_coords(o)
            if square_of_distance(x, y, xo, yo) <= R2 + 1:  # is + 1 necessary?
                return o

    def units_from_mouserect(self, pos, pos2):
        result = []
        self._update_coefs()
        x, y = pos
        x2, y2 = pos2
        if x > x2:
            x, x2 = x2, x
        if y > y2:
            y, y2 = y2, y
        for o in self.interface.units():
            xo, yo = self._object_coords(o)
            if x < xo < x2 and y < yo < y2:
                result.append(o.id)
        return result

    def display_attack(self, attacker_id, target):
        a = self.interface.dobjets[attacker_id]
        self._update_coefs()
        if self.interface.player.is_an_enemy(a):
            color = (255, 0, 0)
        else:
            color = (0, 255, 0)
        r1 = pygame.draw.line(
            get_screen(),
            color,
            self._object_coords(target),
            self._object_coords(a),
        )
        r2 = pygame.draw.circle(
            get_screen(),
            (100, 100, 100),
            self._object_coords(target),
            R * 3 // 2,
            0,
        )
        pygame.display.update(r1.union(r2))
