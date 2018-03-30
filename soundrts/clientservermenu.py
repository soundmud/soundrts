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


class _ServerMenu(Menu):

    def __init__(self, server):
        self.server = server
        Menu.__init__(self)

    def _process_server_event(self, s):
        e = s.strip().split(" ")
        try:
            cmd = getattr(self, "srv_" + e[0])
        except AttributeError:
            if e[0] == "all_orders":
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
            if self.end_loop: # when "quit" is received
                # stop reading
                info("stopped reading server lines because end_loop")
                return

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self._process_available_server_lines() # to avoid empty menus
            self.step()
            voice.update() # for voice.info()
            time.sleep(.01)

    login = None

    def srv_update_menu(self, unused_args):
        self.update_menu(self.make_menu())

    def srv_quit(self, unused_args):
        voice.flush()
        self.end_loop = True

    def srv_sequence(self, args):
        play_sequence(args)

    def srv_e(self, args):
        assert args[0].split(",")[0] == 'new_player'
        login = args[0].split(",")[1]
        if login != self.server.login:
            voice.info([login] + mp.HAS_JUST_LOGGED_IN)
##        if login not in self.players:
##            self.players.append(login)

    def srv_msg(self, args):
        voice.info(*eval_msg_and_volume(" ".join(args)))


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
        GameAdminMenu(self.server).loop()

    def srv_game_guest_menu(self, unused_args):
        GameGuestMenu(self.server).loop()


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
                    menu.append([p,] + style.get(r, "title"),
                                (self.server.write_line,
                                 "faction %s %s" % (pn, r)))

    def srv_start_game(self, args):
        players, alliances, factions = zip(*[p.split(",") for p in args[0].split(";")])
        alliances = map(int, alliances)
        me = args[1]
        seed = int(args[2])
        speed = float(args[3])
        game = MultiplayerGame(self.map, players, me, self.server, seed, speed)
        game.alliances = alliances
        game.factions = factions
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
        if len(self.registered_players) >= self.map.nb_players_min:
            menu.append(mp.START, (self.server.write_line, "start"))
        for pn, (p, pa, pr) in enumerate(self.registered_players):
            pa = int(pa)
            for a in range(1, len(self.registered_players) + 1):
                if a != pa:
                    menu.append(mp.MOVE + [p] + mp.TO_ALLIANCE + nb2msg(a),
                                (self.server.write_line,
                                 "move_to_alliance %s %s" % (pn, a)))
            if p in (self.server.login, "ai"):
                self._add_faction_menu(menu, pn, p, pr)
        menu.append(mp.CANCEL + mp.CANCEL_THIS_GAME,
                    (self.server.write_line, "cancel_game"))
        return menu

    def srv_available_players(self, args):
        self.available_players = args


class GameGuestMenu(_BeforeGameMenu):

    def _get_player(self):
        for pn, (p, pa, pr) in enumerate(self.registered_players):
            if p == self.server.login:
                return pn, p, pr

    def make_menu(self):
        menu = Menu(self.map.title)
        self._add_faction_menu(menu, *self._get_player())
        menu.append(mp.QUIT2 + mp.LEAVE_THIS_GAME,
                    (self.server.write_line, "unregister"))
        return menu
