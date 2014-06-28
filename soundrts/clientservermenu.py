from clientmenu import *
from clientstyle import load_style, get_style
from game import MultiplayerGame
import mapfile


class _ServerMenu(Menu):

    def __init__(self, server):
        self.server = server
        Menu.__init__(self)

    def _process_server_event(self, s):
        debug("server event: %s", s)
        cmd_args = s.strip().split(" ")
        cmd = "srv_" + cmd_args[0]
        args = cmd_args[1:]
        if hasattr(self, cmd):
            return getattr(self, cmd)(args)
        elif cmd == "srv_all_orders":
            debug("ignored by ServerMenu: %s", s)
        elif cmd != "srv_":
            warning("not recognized by ServerMenu: %s", s)

    def _process_server(self):
        s = self.server.read_line()
        if s is None:
            self.server_is_done = True # don't read more
        elif re.match(r'^msg \[[0-9a-zA-Z, \.\[\]"\']+\]$', s):
            voice.info(*eval(s.split(' ', 1)[1]))
        else:
            self._process_server_event(s)

    def loop(self):
        debug("%s loop...", self.__class__.__name__)
        self.end_loop = False
        while not self.end_loop:
            self.server_is_done = False
            while not self.server_is_done: # avoid menus with no choices
                self._process_server()
                if self.end_loop:
                    debug("break loop because end_loop")
                    break # when "quit" is received
            self.step()
            voice.update() # for voice.info()
            time.sleep(.01)
        debug("...end %s loop", self.__class__.__name__)

    login = None

    def srv_update_menu(self, unused_args):
        self.update_menu(self.make_menu())

    def srv_quit(self, unused_args):
        voice.flush()
        self.end_loop = True

    def srv_sequence(self, args):
        sounds.play_sequence(args)

    def srv_e(self, args):
        assert args[0].split(",")[0] == 'new_player'
        login = args[0].split(",")[1]
        if login != self.server.login:
            voice.info([login, 4240]) # ... has just logged in
##        if login not in self.players:
##            self.players.append(login)

    def srv_msg(self, args):
        voice.info(*eval_msg_and_volume(" ".join(args)))


class ServerMenu(_ServerMenu):

    invitations = ()

    def _create_game(self, args):
        n, title = args
        Menu([4055] + title,
             [([4103], (self.server.write_line, "create %s 0.5" % n)),
              ([4104], (self.server.write_line, "create %s 1.0" % n)),
              ([4105] + nombre(2), (self.server.write_line, "create %s 2.0" % n)),
              ([4105] + nombre(4), (self.server.write_line, "create %s 4.0" % n)),
              ([4048], None),
              ],
             default_choice_index=1).run() # XXX not a ServerMenu
        
    def _get_creation_submenu(self):
        menu = Menu([4055])
        for n, m in enumerate(self.maps):
            menu.append(m, (self._create_game, (n, m)))
        menu.append([4048], None)
        return menu

    def make_menu(self):
        menu = Menu()
        for g in self.invitations:
            menu.append([4053] + g[1:], (self.server.write_line, "register %s" % g[0]))
        menu.append([4055], self._get_creation_submenu())
        menu.append([4041], (self.server.write_line, "quit"))
        return menu

    def srv_welcome(self, args):
        self.server.login, server_login = args
        voice.important([4056, self.server.login, 4260, server_login])

    def srv_invitations(self, args):
        self.invitations = [x.split(",") for x in args]

    def srv_maps(self, args):
        self.maps = [x.split(",") for x in args]

    def srv_game_admin_menu(self, unused_args):
        GameAdminMenu(self.server).loop()

    def srv_game_guest_menu(self, unused_args):
        GameGuestMenu(self.server).loop()


class _BeforeGameMenu(_ServerMenu):

    map_title = ()
    registered_players = ()

    def srv_map_title(self, args):
        self.map_title = args

    def srv_map_races(self, args):
        self.map_races = args
        load_style(res.get_text("ui/style", append=True, locale=True)) # XXX: won't work with races defined in the map
#       TODO: use self.map.additional_style (and self.map.campaign_style ?)

    def srv_registered_players(self, args):
        self.registered_players = [p.split(",") for p in args]

    def _add_race_menu(self, menu, pn, p, pr):
        if len(self.map_races) > 1:
            for r in ["random_race"] + self.map_races:
                if r != pr:
                    menu.append([p,] + get_style(r, "title"),
                                (self.server.write_line,
                                 "race %s %s" % (pn, r)))

    def srv_start_game(self, args):
        players, alliances, races = zip(*[p.split(",") for p in args[0].split(";")])
        alliances = map(int, alliances)
        me = args[1]
        seed = int(args[2])
        speed = float(args[3])
        server_map = mapfile.Map()
        server_map.unpack(" ".join(args[4:])) # warning: args is splitted from a stripped string
        game = MultiplayerGame(server_map, players, me, self.server, seed, speed)
        game.alliances = alliances
        game.races = races
        game.run()
        self.end_loop = True


class GameAdminMenu(_BeforeGameMenu):

    available_players = ()
    nb_players_min = nb_players_max = 0

    def make_menu(self):
        menu = Menu(self.map_title)
        if len(self.registered_players) < self.nb_players_max:
            for p in self.available_players:
                menu.append([4058, p],
                            (self.server.write_line, "invite %s" % p))
            menu.append([4058, 4258], (self.server.write_line, "invite_easy"))
            menu.append([4058, 4257],
                        (self.server.write_line, "invite_aggressive"))
        if len(self.registered_players) >= self.nb_players_min:
            menu.append([4059], (self.server.write_line, "start"))
        for pn, (p, pa, pr) in enumerate(self.registered_players):
            pa = int(pa)
            for a in range(1, len(self.registered_players) + 1):
                if a != pa:
                    menu.append([4284, p, 4285] + nombre(a),
                                (self.server.write_line,
                                 "move_to_alliance %s %s" % (pn, a)))
            if p in (self.server.login, "ai"):
                self._add_race_menu(menu, pn, p, pr)
        menu.append([4048, 4060], (self.server.write_line, "cancel_game"))
        return menu

    def srv_map_nb_players(self, args):
        self.nb_players_min, self.nb_players_max = map(int, args)

    def srv_available_players(self, args):
        self.available_players = args


class GameGuestMenu(_BeforeGameMenu):

    def _get_player(self):
        for pn, (p, pa, pr) in enumerate(self.registered_players):
            if p == self.server.login:
                return pn, p, pr

    def make_menu(self):
        menu = Menu(self.map_title)
        self._add_race_menu(menu, *self._get_player())
        menu.append([4041, 4061], (self.server.write_line, "unregister"))
        return menu
