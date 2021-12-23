import asynchat
import re
import sys
import time
from typing import TYPE_CHECKING

from .lib.log import exception, info, warning
from .lib.msgs import encode_msg
from .mapfile import worlds_multi

if TYPE_CHECKING:
    from .servermain import Server

from .serverroom import (
    Anonymous,
    Game,
    InTheLobby,
    OrganizingAGame,
    WaitingForTheGameToStart,
    _State,
)


class ConnectionToClient(asynchat.async_chat):

    is_disconnected = False
    login = None
    version = None
    game = None

    def __init__(self, server: "Server", connection_and_address) -> None:
        (connection, address) = connection_and_address
        asynchat.async_chat.__init__(self, connection)
        self.id = server.get_next_id()
        self.set_terminator(b"\n")
        self.server = server
        self.inbuffer = b""
        self.address = address
        self.state: _State = Anonymous()
        self.push(":")
        self.t1 = time.time()

    def push(self, s):
        return asynchat.async_chat.push(self, s.encode("ascii"))

    @property
    def name(self):
        return [self.login]

    def collect_incoming_data(self, data):
        self.inbuffer += data

    def _execute_command(self, data):
        args = data.decode("ascii").split(" ")
        if args[0] not in self.state.allowed_commands:
            warning("action not allowed: %s" % args[0])
            return
        cmd = "cmd_" + args[0]
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning("action unknown: %s" % args[0])

    def found_terminator(self):
        data = self.inbuffer.replace(b"\r", b"")
        self.inbuffer = b""
        try:
            self._execute_command(data)
        except SystemExit:
            raise
        except:
            exception("error executing command: %s" % data)

    def handle_close(self):
        try:
            self.server.remove_client(self)
        except SystemExit:
            raise
        except:
            try:
                exception("error")
            except:
                pass
        self.close()

    def handle_error(self):
        if sys.exc_info()[0] in [SystemExit, KeyboardInterrupt]:
            sys.exit()
        else:
            self.handle_close()

    def send_invitations(self):
        self.push(
            "invitations %s\n"
            % " ".join(
                [
                    ",".join([str(x) for x in [g.id, g.admin.login] + g.scenario.title])
                    for g in self.server.games
                    if self in g.guests
                ]
            )
        )

    def notify(self, *args):
        if not self.is_disconnected:
            self.push(" ".join(map(str, args)) + "\n")

    def send_maps(self):
        if self.server.can_create(self):
            self.push(
                "maps %s\n"
                % " ".join(
                    [",".join([str(y) for y in x.title]) for x in worlds_multi()]
                )
            )
        else:
            self.push("maps \n")

    def is_compatible(self, client):
        return self.version == client.version

    # "anonymous" commands

    def _unique_login(self, client_login):
        if client_login.startswith("ai_"):
            client_login = "player"
        login = client_login
        n = 2
        while login in [x.login for x in self.server.clients]:
            login = client_login + str(n)
            n += 1
        return login

    def _get_version_and_login_from_data(self, data):
        try:
            version, login = data.split(" ", 1)
        except:
            warning("can't extract version and login: %s" % data)
            return (None, None)
        if re.match("^[a-zA-Z0-9]{1,20}$", login) == None:
            warning("bad login: %s" % login)
            return (version, None)
        if len(self.server.clients) >= self.server.nb_clients_max:
            warning("refused client %s: too many clients." % login)
            return (version, None)
        return (version, self._unique_login(login))

    @property
    def compatible_clients(self):
        return [c.login for c in self.server.clients if c.is_compatible(self)]

    def _send_server_status(self):
        self.notify("clients", *self.compatible_clients)
        for game in self.server.games:
            if game.started:
                self.notify("game", *game.short_status)

    def _accept_client_after_login(self):
        self.delay = time.time() - self.t1
        info(
            "new player: IP=%s login=%s version=%s delay=%s"
            % (self.address[0], self.login, self.version, self.delay)
        )
        # welcome client to server
        self.push("ok!\n")
        self.push(f"welcome {self.login} {self.server.login}\n")
        self.server.clients.append(self)
        # move client to lobby
        self.state = InTheLobby()
        # alert lobby and game admins
        for c in self.server.available_players() + self.server.game_admins():
            if c.is_compatible(self):
                c.notify("logged_in", self.login)
        self._send_server_status()
        for g in self.server.games:
            g.notify_connection_of(self)
        self.server.log_status()

    def cmd_login(self, args):
        self.version, self.login = self._get_version_and_login_from_data(" ".join(args))
        if self.login is not None:
            self._accept_client_after_login()
            self.server.update_menus()
        else:
            info("incorrect login")
            self.handle_close()  # disconnect client

    # "in the lobby" commands

    def cmd_create(self, args: str) -> None:
        if self.server.can_create(self):
            self.state = OrganizingAGame()
            self.push("game_admin_menu\n")
            scs = worlds_multi()
            try:
                scenario = scs[int(args[0])]
            except ValueError:
                for scenario in scs:
                    if args[0] in scenario.path:
                        break
            self.push("map %s\n" % scenario.pack().decode())
            speed = float(args[1])
            is_public = len(args) >= 3 and args[2] == "public"
            self.server.games.append(
                Game(scenario, speed, self.server, self, is_public)
            )
            self.server.update_menus()
        else:
            warning("game not created (max number reached)")
            self.notify("too_many_games")

    def cmd_register(self, args: str) -> None:
        game = self.server.get_game_by_id(args[0])
        if game is not None and game.can_register():
            self.state = WaitingForTheGameToStart()
            self.push("game_guest_menu\n")
            self.push("map %s\n" % game.scenario.pack().decode())
            game.register(self)
            self.server.update_menus()
        else:
            self.notify("register_error")

    def cmd_quit(self, unused_args):
        # When the client wants to quit, he first sends "quit" to the server.
        # Then the server knows he musn't send commands anymore. He warns the
        # client: "ok, you can quit". Then the client closes the connection
        # and then, and only then, the server forgets the client.
        self.push("quit\n")
        # self.is_quitting = True

    # "organizing a game" commands

    def cmd_cancel_game(self, unused_args):
        self.game.cancel()
        self.server.update_menus()

    def cmd_invite(self, args):
        guest = self.server.get_client_by_login(args[0])
        if (
            guest
            and guest in self.server.available_players()
            and guest.is_compatible(self)
        ):
            self.game.invite(guest)
            self.server.update_menus()
        else:
            self.notify("invite_error")

    def cmd_invite_easy(self, unused_args):
        self.game.invite_computer("easy")
        self.send_menu()  # only the admin

    def cmd_invite_aggressive(self, unused_args):
        self.game.invite_computer("aggressive")
        self.send_menu()  # only the admin

    def cmd_invite_ai2(self, unused_args):
        self.game.invite_computer("ai2")
        self.send_menu()  # only the admin

    def cmd_move_to_alliance(self, args):
        self.game.move_to_alliance(args[0], args[1])
        self.send_menu()  # only the admin

    def cmd_start(self, unused_args):
        self.game.start()  # create chosen world
        self.server.update_menus()

    def cmd_faction(self, args):
        self.game.set_faction(args[0], args[1])
        self.server.update_menus()

    # "waiting for the game to start" commands

    def cmd_unregister(self, unused_args):
        self.game.unregister(self)
        self.server.update_menus()

    # "playing" commands

    def cmd_orders(self, args):
        self.push("pong\n")
        self.game.orders(self, *args)

    def cmd_quit_game(self, unused_args):
        self.game.orders(self, "quit")
        self.game.remove(self)
        self.state = InTheLobby()
        self.server.update_menus()

    def cmd_timeout(self, unused_args):
        self.game.check_timeout()

    # wrapper

    def send_menu(self):
        self.state.send_menu(self)

    # misc

    def send_msg(self, msg):
        self.push("msg %s\n" % encode_msg(msg))

    def cmd_debug_info(self, args):
        info(" ".join(args))

    def cmd_say(self, args):
        if self.game:
            clients = self.game.human_players
        else:
            clients = self.server.available_players()
        for client in clients:
            client.notify("say", self.login, *args)
