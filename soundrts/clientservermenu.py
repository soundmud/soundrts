import re
import time

from clientmedia import voice, sounds, play_sequence
from clientmenu import Menu
from definitions import style
from game import MultiplayerGame
from lib.log import info, warning
import mapfile
import msgparts as mp
from lib.msgs import nb2msg, eval_msg_and_volume
import res


def insert_silences(msg):
    result = msg[:1]
    for sound in msg[1:]:
        result += mp.PERIOD + [sound]
    return result

def game_short_status(map_title, clients, minutes):
    clients = clients.split(",")
    players = insert_silences(sum([name(c) for c in clients], []))
    msg = mp.MULTIPLAYER + [map_title] + mp.PERIOD \
           + players + mp.PERIOD \
           + nb2msg(minutes) + mp.MINUTES
    return msg


class _ServerMenu(Menu):

    def __init__(self, server, auto=False):
        self.server = server
        self.auto = auto
        Menu.__init__(self)

    def _process_server_event(self, s):
        e = s.strip().split(" ")
        try:
            cmd = getattr(self, "srv_" + e[0])
        except AttributeError:
            if e[0] in ("all_orders", "pong"):
                info("ignored by ServerMenu: %s", s)
            elif e[0]:
                warning("not recognized by ServerMenu: %s", s)
        else:
            cmd(e[1:])

    def _process_available_server_lines(self):
        while True:
            s = self.server.read_line()
            if s is None: return
            self._process_server_event(s)
            if self.end_loop: # received "quit"
                # stop reading
                return

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self._process_available_server_lines() # to avoid empty menus
            self.step()
            if self.auto:
                if self.auto[0].run(self):
                    del self.auto[0]
            voice.update() # for voice.info()
            time.sleep(.01)

    def push(self, line):
        self.server.write_line(line)

    login = None

    def srv_update_menu(self, unused_args):
        self.update_menu(self.make_menu())

    def srv_quit(self, unused_args):
        voice.flush()
        self.end_loop = True

    def srv_say(self, args):
        login, msg = args[0], args[1:]
        voice.info([login] + mp.SAYS + [" ".join(msg)])

    def srv_sequence(self, args):
        play_sequence(args)

    def srv_logged_in(self, args):
        login, = args
        if login != self.server.login:
            voice.info([login] + mp.HAS_JUST_LOGGED_IN)

    def srv_logged_out(self, args):
        login, = args
        voice.info([login] + mp.HAS_JUST_LOGGED_OUT)

    def srv_msg(self, args):
        voice.info(*eval_msg_and_volume(" ".join(args)))

    def srv_invite_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_invite_computer_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_register_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_too_many_games(self, unused_args):
        voice.info(mp.TOO_MANY_GAMES)

    def srv_clients(self, args):
        msg = insert_silences(sum([name(c) for c in args], []))
        voice.info(msg)

    def srv_game(self, args):
        voice.info(game_short_status(*args))

    def srv_invitation(self, args):
        admin_login, map_title = args
        voice.info([admin_login] + mp.INVITES_YOU + [map_title])

    def _players_names(self, players):
        return insert_silences(sum([name(p) for p in players], []))

    def _game_status(self, players):
        msg = nb2msg(len(players)) + mp.PLAYERS_ON + nb2msg(self.map.nb_players_max)
        if len(players) >= self.map.nb_players_min:
            msg += mp.THE_GAME_WILL_START_WHEN_ORGANIZER_IS_READY
        else:
            msg += mp.NOT_ENOUGH_PLAYERS + nb2msg(self.map.nb_players_min)
        msg += mp.PERIOD + self._players_names(players)
        return msg

    def srv_registered(self, args):
        player_login, players = args
        players = players.split(",")
        voice.info(name(player_login) + mp.HAS_JUST_JOINED + self._game_status(players))

    def srv_alliance(self, args):
        player_login, alliance = args
        voice.info(mp.MOVE + name(player_login) + mp.TO_ALLIANCE + nb2msg(alliance))

    def srv_faction(self, args):
        player_login, faction = args
        faction_name = style.get(faction, 'title')
        voice.info(name(player_login) + faction_name)


class ServerMenu(_ServerMenu):

    invitations = ()

    def _get_speed_submenu(self, args):
        n, title, is_public = args
        def create_with_speed(speed):
            s = "create %s %s %s" % (n, speed, is_public)
            return (self.server.write_line, s)
        Menu(title,
             [(mp.SET_SPEED_TO_SLOW, create_with_speed("0.5")),
              (mp.SET_SPEED_TO_NORMAL, create_with_speed("1.0")),
              (mp.SET_SPEED_TO_FAST + nb2msg(2), create_with_speed("2.0")),
              (mp.SET_SPEED_TO_FAST + nb2msg(4), create_with_speed("4.0")),
              (mp.CANCEL, None),
              ],
             default_choice_index=1).run()

    def _get_creation_submenu(self, is_public=""):
        if is_public == "public":
            title = mp.START_A_PUBLIC_GAME_ON
        else:
            title = mp.START_A_GAME_ON
        menu = Menu(title, remember="mapmenu")
        for n, m in enumerate(self.maps):
            menu.append(m, (self._get_speed_submenu, (n, title + m, is_public)))
        menu.append(mp.CANCEL, None)
        return menu

    def make_menu(self):
        menu = Menu()
        for g in self.invitations:
            menu.append(mp.ACCEPT_INVITATION_FROM + g[1:],
                        (self.server.write_line, "register %s" % g[0]))
        menu.append(mp.START_A_GAME_ON, self._get_creation_submenu())
        menu.append(mp.START_A_PUBLIC_GAME_ON,
                    self._get_creation_submenu("public"))
        menu.append(mp.QUIT2, (self.server.write_line, "quit"))
        return menu

    def srv_welcome(self, args):
        self.server.login, server_login = args
        voice.important(mp.WELCOME + [self.server.login]
                        + mp.ON_THE_SERVER_OF + [server_login])

    def srv_invitations(self, args):
        self.invitations = [x.split(",") for x in args]

    def srv_maps(self, args):
        self.maps = [x.split(",") for x in args]

    def srv_game_admin_menu(self, unused_args):
        GameAdminMenu(self.server, auto=self.auto).loop()

    def srv_game_guest_menu(self, unused_args):
        GameGuestMenu(self.server, auto=self.auto).loop()


def name(login):
    if login == "ai_easy":
        return mp.QUIET_COMPUTER
    if login == "ai_aggressive":
        return mp.AGGRESSIVE_COMPUTER
    return [login]

##    @property
##    def name(self):
##        if self.level == "easy":
##            return mp.QUIET_COMPUTER
##        elif self.level == "aggressive":
##            return mp.AGGRESSIVE_COMPUTER
##        return [self.login]


class _BeforeGameMenu(_ServerMenu):

    registered_players = ()

    def srv_map(self, args):
        self.map = mapfile.Map()
        self.map.unpack(" ".join(args)) # warning: args is split from a stripped string
        self.map.load_style(res)

    def srv_registered_players(self, args):
        self.registered_players = [p.split(",") for p in args]

    def _add_faction_menu(self, menu, pn, p, pr):
        if len(self.map.factions) > 1:
            for r in ["random_faction"] + self.map.factions:
                if r != pr:
                    menu.append(name(p) + style.get(r, "title"),
                                (self.server.write_line,
                                 "faction %s %s" % (pn, r)))

    def srv_start_game(self, args):
        players, local_login, seed, speed = args
        players = [p.split(",") for p in players.split(";")]
        seed = int(seed)
        speed = float(speed)
        game = MultiplayerGame(self.map, players, local_login, self.server, seed, speed)
        game.run()
        self.end_loop = True


class GameAdminMenu(_BeforeGameMenu):

    available_players = ()

    def make_menu(self):
        menu = Menu(self.map.title)
        if len(self.registered_players) < self.map.nb_players_max:
            for p in self.available_players:
                menu.append(mp.INVITE + [p],
                            (self.server.write_line, "invite %s" % p))
            menu.append(mp.INVITE + mp.QUIET_COMPUTER,
                        (self.server.write_line, "invite_easy"))
            menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER,
                        (self.server.write_line, "invite_aggressive"))
            menu.append(mp.INVITE + mp.AGGRESSIVE_COMPUTER + nb2msg(2),
                        (self.server.write_line, "invite_ai2"))
        if len(self.registered_players) >= self.map.nb_players_min:
            menu.append(mp.START, (self.server.write_line, "start"))
        for pn, (login, pa, pr) in enumerate(self.registered_players):
            pa = int(pa)
            for a in range(1, len(self.registered_players) + 1):
                if a != pa:
                    menu.append(mp.MOVE + name(login) + mp.TO_ALLIANCE + nb2msg(a),
                                (self.server.write_line,
                                 "move_to_alliance %s %s" % (pn, a)))
            if login == self.server.login or login.startswith("ai_"):
                self._add_faction_menu(menu, pn, login, pr)
        menu.append(mp.CANCEL + mp.CANCEL_THIS_GAME,
                    (self.server.write_line, "cancel_game"))
        return menu

    def srv_available_players(self, args):
        self.available_players = args


class GameGuestMenu(_BeforeGameMenu):

    def _get_player(self):
        for pn, (login, pa, pr) in enumerate(self.registered_players):
            if login == self.server.login:
                return pn, login, pr

    def make_menu(self):
        menu = Menu(self.map.title)
        self._add_faction_menu(menu, *self._get_player())
        menu.append(mp.QUIT2 + mp.LEAVE_THIS_GAME,
                    (self.server.write_line, "unregister"))
        return menu
