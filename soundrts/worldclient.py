try: 
    from hashlib import md5
except ImportError:
    from md5 import md5
import platform
import sys
import time
import urllib

from commun import VERSION
from constants import *
from lib.log import *



def send_error_to_metaserver(error_msg):
    try:
        params = urllib.urlencode({"method": "add", "msg": error_msg})
        urllib.urlopen(METASERVER_URL + "errors.php?%s" % params).read()
    except:
        exception("could not send error message to web server")

def send_platform_version_to_metaserver(game, nb):
    error_msg = "not_an_error time=%s soundrts=%s map=%s players=%s platform=%s python=%s" % (
        time.time(),
        VERSION,
        game,
        nb,
        platform.platform(),
        sys.version.replace("\n", " "),
        )
    send_error_to_metaserver(error_msg)


class DummyClient(object):

    login = "ai"

    def __init__(self, AI_type="timers"):
        self.AI_type = AI_type

    def push(self, *args):
        pass


class HalfDummyClient(DummyClient):

    def __init__(self, login):
        self.login = login


class DirectClient(object):

    player = None
    data = ""

    def __init__(self, login, game_session):
        self.login = login
        self.game_session = game_session

    def write_line(self, s):
        if s == "no_end_of_update_yet":
            debug("received no_end_of_update_yet")
            return
        if self.player:
            self.player.world.queue_command(self.player, s)
            debug("client: %s", s)
        else:
            debug("couldn't send client command (no player): %s", s)

    def push(self, *args):
        self.interface.process_server_event(*args)

    def has_victory(self):
        return self.player.has_victory

    def save_game(self):
        self.game_session.save()


class Coordinator(object):

    data = ""
    world = None
    
    def __init__(self, login, main_server, clients):
        self.login = login
        self.main_server = main_server
        self.clients = clients
        self.orders = ""
        self.orders_digest = md5()
        self._all_orders = ""
        self._previous_update = time.time()

    def get_client_by_login(self, login):
        for c in self.clients:
            if c.login == login:
                return c

    # communications with the client game interface

    def write_line(self, s):
        if s == "no_end_of_update_yet":
            self.get_all_orders_from_server()
            return
        self.orders += s + "\n"
        if s == "update":
            if self.world is None:
                self.world = self.clients[0].player.world
            self.main_server.write_line(
                "orders %s %s" %
                (
                    self.orders.replace("\n", NEWLINE_REPLACEMENT).replace(" ", SPACE_REPLACEMENT),
                    self.get_digest(),
                 )
                )
            self.orders = ""
            self.get_all_orders_from_server()

    # communications with the world

    def get_digest(self):
        d = md5(self.orders_digest.hexdigest())
        d.update(self.world.get_digest())
        return d.hexdigest()

    def get_sync_debug_msg_1(self):
        return "out_of_sync_error: map=%s version=%s platform=%s python=%s md5=%s" % (
            self.world.map.get_name(), VERSION, platform.platform(), sys.version.replace("\n", " "),
            self.get_digest(), )

    def get_sync_debug_msg_2(self):
        return "out_of_sync_error:debug_info orders=%s objects=%s" % (
               self._all_orders,
               self.world.get_objects_string()[-150:],
               )

    def get_all_orders_from_server(self):
        # assertion: the orders arrive in the right order (guaranteed by the server)
        for s in self.main_server.read_line():
            debug("main server data for %s: %s", self.login, s)
            args = s.split()
            if args[0] == "all_orders":
                self._previous_update = time.time()
                self.orders_digest.update(s) # used by the synchronization debugger
                players_orders = args[1:]
                for player_orders in players_orders:
                    player, orders = player_orders.split("/")
                    orders = orders.replace(NEWLINE_REPLACEMENT, "\n").replace(SPACE_REPLACEMENT, " ")
                    for order in orders.strip().split("\n"): # strip() to remove empty order at the end of the list
                        direct_player = self.get_client_by_login(player).player
                        if direct_player:
                            debug("player: %s  order: %s", player, order)
                            direct_player.world.queue_command(direct_player, order)
                        if order != "update" and not order.startswith("control"):
                            self._all_orders += order.replace("order 0 0 ", "") + ";"
                            self._all_orders = self._all_orders[-100:]
            elif args[0] == "synchronization_error":
                try:
                    send_error_to_metaserver(self.get_sync_debug_msg_1())
                    send_error_to_metaserver(self.get_sync_debug_msg_2())
                except:
                    exception("error sending sync debug data")
            else:
                warning("ignored data from server: %s", s)
        # check for timeout and alert server
        if time.time() > self._previous_update + 5.0:
            self.main_server.write_line("timeout")
            self._previous_update += 5.0

    def push(self, *args):
        self.interface.process_server_event(*args)
