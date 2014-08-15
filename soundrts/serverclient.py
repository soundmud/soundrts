import asynchat
import re
import string
import sys
import time

from lib.log import debug, info, warning, exception
from msgs import insert_silences, encode_msg
from multimaps import worlds_multi
from serverroom import Anonymous, InTheLobby, OrganizingAGame, WaitingForTheGameToStart, Game
from version import COMPATIBILITY_VERSION


class ConnectionToClient(asynchat.async_chat):

    is_disconnected = False
    login = None
    game = None

    def __init__(self, server, (connection, address)):
        info("Connected: %s:%s" % address)
        asynchat.async_chat.__init__(self, connection)
        self.id = server.get_next_id()
        self.set_terminator('\n')
        self.server = server
        self.inbuffer = ''
        self.address = address
        self.state = Anonymous()
        self.push(":")
        self.t1 = time.time()

    def collect_incoming_data(self, data):
        self.inbuffer += data

    def _execute_command(self, data):
        args = string.split(data)
        if args[0] not in self.state.allowed_commands:
            warning("action not allowed: %s" % args[0])
            return
        cmd = "cmd_" + args[0]
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning("action unknown: %s" % args[0])

    def found_terminator(self):
        data = string.replace(self.inbuffer, "\r", "")
        debug("server data from %s: %s", self.login, data)
        self.inbuffer = ''
        try:
            self._execute_command(data)
        except SystemExit:
            raise
        except:
            exception("error executing command: %s" % data)

    def handle_close(self):
        try:
            debug("ConnectionToClient.handle_close")
        except:
            pass
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
        try:
            debug("ConnectionToClient.handle_error %s", sys.exc_info()[0])
        except:
            pass
        if sys.exc_info()[0] in [SystemExit, KeyboardInterrupt]:
            sys.exit()
        else:
            self.handle_close()

    def send_invitations(self):
        self.push("invitations %s\n" %
            " ".join([
            ",".join([str(x) for x in [g.id, g.admin.login] + g.scenario.title])
            for g in self.server.games if self in g.guests]))
        
    def send_maps(self):
        if self.server.can_create(self):
            self.push("maps %s\n" %
                      " ".join([",".join([str(y) for y in x.title])
                                for x in worlds_multi()]))
        else:
            self.push("maps \n")

    def send_e(self, event):
        self.push("e %s\n" % event)

    # "anonymous" commands

    def _unique_login(self, client_login):
        login = client_login
        n = 2
        # "ai" (or "npc_ai") is reserved
        # (used to forbid cheatmode in multiplayer games)
        while login in [x.login for x in self.server.clients] + ["ai", "npc_ai"]:
            login = client_login + "%s" % n
            n += 1
        return login

    def _get_login_from_data(self, data):
        try:
            version, login = data.split(" ", 1)
        except:
            warning("can't extract version and login: %s" % data)
            return
        if version != COMPATIBILITY_VERSION:
            warning("bad client version: %s" % version)
            return
        if re.match("^[a-zA-Z0-9]{1,20}$", login) == None:
            warning("bad login: %s" % login)
            return
        if len(self.server.clients) >= self.server.nb_clients_max:
            warning("refused client %s: too many clients." % login)
            return
        return self._unique_login(login)

    def _send_server_status_msg(self):
        self.send_msg(insert_silences([c.login for c in self.server.clients]))
        for g in self.server.games:
            if g.started:
                self.send_msg(g.get_status_msg())

    def _accept_client_after_login(self):
        self.delay = time.time() - self.t1
        info("new player: IP=%s login=%s delay=%s" %
             (self.address[0], self.login, self.delay))
        # welcome client to server
        self.push("ok!\n")
        self.push("welcome %s %s\n" % (self.login, self.server.login))
        self.server.clients.append(self)
        # move client to lobby
        self.state = InTheLobby()
        # alert lobby and game admins
        for c in self.server.available_players() + self.server.game_admins():
            c.send_e("new_player,%s" % self.login)
        self._send_server_status_msg()
        self.server.log_status()

    def cmd_login(self, args):
        self.login = self._get_login_from_data(" ".join(args))
        if self.login is not None:
            self._accept_client_after_login()
            self.server.update_menus()
        else:
            info("incorrect login")
            self.handle_close() # disconnect client

    # "in the lobby" commands

    def cmd_create(self, args):
        if self.server.can_create(self):
            self.state = OrganizingAGame()
            self.push("game_admin_menu\n")
            scs = worlds_multi()
            scenario = scs[int(args[0])]
            speed = float(args[1])
            self.server.games.append(Game(scenario, speed, self.server, self))
            self.server.update_menus()
        else:
            warning("game not created (max number reached)")
            self.send_msg([4057])

    def cmd_register(self, args):
        game = self.server.get_game_by_id(args[0])
        if game is not None and game.can_register():
            self.state = WaitingForTheGameToStart()
            self.push("game_guest_menu\n")
            game.register(self)
            self.server.update_menus()
        else:
            self.send_msg([1029]) # hostile sound

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
        if guest and guest in self.server.available_players():
            self.game.invite(guest)
            self.server.update_menus()
        else:
            self.send_msg([1029]) # hostile sound

    def cmd_invite_easy(self, unused_args):
        self.game.invite_computer("easy")
        self.send_menu() # only the admin

    def cmd_invite_aggressive(self, unused_args):
        self.game.invite_computer("aggressive")
        self.send_menu() # only the admin

    def cmd_move_to_alliance(self, args):
        self.game.move_to_alliance(args[0], args[1])
        self.send_menu() # only the admin

    def cmd_start(self, unused_args):
        self.game.start() # create chosen world
        self.server.update_menus()

    def cmd_race(self, args):
        self.game.set_race(args[0], args[1])
        self.server.update_menus()

    # "waiting for the game to start" commands

    def cmd_unregister(self, unused_args):
        self.game.unregister(self)
        self.server.update_menus()

    # "playing" commands

    def cmd_orders(self, args):
        self.game.orders(self, args)

    def cmd_quit_game(self, unused_args):
        self.game.quit_game(self)
        self.server.update_menus()

    def cmd_abort_game(self, unused_args):
        self.game.abort_game(self)
        self.server.update_menus()

    def cmd_timeout(self, unused_args):
        self.game.check_timeout()

    # wrapper

    def send_menu(self):
        self.state.send_menu(self)

    # misc

    def send_msg(self, msg):
        self.push("msg %s\n" % encode_msg(msg))

    def login_to_send(self):
        return self.login

    def cmd_debug_info(self, args):
        info(" ".join(args))

    def cmd_say(self, args):
        msg = [self.login] + [4287] + [" ".join(args)]
        if self.game is not None:
            self.game.broadcast(msg)
        else:
            for p in self.server.available_players():
                p.send_msg(msg)
