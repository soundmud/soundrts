try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import platform
import sys
import time
import urllib

from version import VERSION, IS_DEV_VERSION
from metaserver import METASERVER_URL
from lib import chronometer as chrono
from lib.log import info, warning, exception
from worldplayercomputer import Computer
from worldplayercomputer2 import Computer2
from worldplayerhuman import Human


FIRST_FPCT = 1

# used for packing the orders
NEWLINE_REPLACEMENT = ";"
SPACE_REPLACEMENT = ","

def _pack(player_orders):
    return player_orders.replace("\n", NEWLINE_REPLACEMENT).replace(" ", SPACE_REPLACEMENT)

def _unpack(player_orders):
    return player_orders.replace(NEWLINE_REPLACEMENT, "\n").replace(SPACE_REPLACEMENT, " ")

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


class _Controller(object):

    @property
    def name(self):
        from clientservermenu import name
        return name(self.login)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.login)

    player_class = Human
    alliance = None
    faction = "random_faction"
    neutral = False


class _Client(_Controller):

    @property
    def allow_cheatmode(self):
        return self.game_session.allow_cheatmode

    def push(self, *args):
        self.interface.queue_srv_event(*args)

    def get_orders(self):
        if not hasattr(self, "_orders"):
            self._orders = []
        self._dispatch_orders()
        result = self._orders
        self._orders = []
        return result

    def queue_command(self, player, s):
        if player not in self.player.world.players:
            info("didn't send the order for player %s: %s", player, s)
            return
        if self.game_session.record_replay:
            player_index = self.player.world.players.index(player)
            self.game_session.replay_write(" ".join(map(str, (self.player.world.time, player_index, s))))
        if not hasattr(self, "_orders"):
            self._orders = []
        self._orders.append((player, s))

    def _dispatch_orders(self):
        pass


class DummyClient(_Controller): # AI

    alliance = "ai" # computer players are allied by default

    def __init__(self, AI_type="timers", neutral=False):
        self.AI_type = AI_type
        self.neutral = neutral
        self.login = "ai_" + self.AI_type

    def push(self, *args):
        pass

    @property
    def player_class(self):
        if self.login == "ai_ai2":
            return Computer2
        else:
            return Computer


class RemoteClient(_Controller):

    def __init__(self, login):
        self.login = login

    def push(self, *args):
        pass


class DirectClient(_Client): # client for single player games

    player = None
    data = ""

    def __init__(self, login, game_session):
        self.login = login
        self.game_session = game_session

    def update(self):
        pass

    def orders_are_ready(self):
        return True

    def write_line(self, s):
        if self.player:
            self.queue_command(self.player, s)
        else:
            warning("couldn't send client command (no player): %s", s)

    def has_victory(self):
        return self.player.has_victory

    def save_game(self):
        self.game_session.save()


class ReplayClient(DirectClient):

    nb_humans = 1

    def write_line(self, s):
        if s == "quit":
            self.queue_command(self.player, "neutral_quit")
        elif not s.startswith(("control", "order")):
            self.queue_command(self.player, s)

    def _dispatch_orders(self):
        while True:
            if not getattr(self, "_cmd", None):
                self._cmd = self.game_session.replay_read()
                if not self._cmd:
                    break
            time, player, command = self._cmd.split(" ", 2)
            if int(time) == self.player.world.time:
                player = self.player.world.players[int(player)]
                self.queue_command(player, command)
                self._cmd = None
            else:
                break


class Coordinator(_Client): # client coordinator for multiplayer games

    data = ""
    world = None
    
    def __init__(self, login, main_server, game_session):
        self.login = login
        self.main_server = main_server
        self.orders = ""
        self._all_orders = ""
        self._previous_update = time.time()
        self.game_session = game_session
        self.all_orders = [[FIRST_FPCT]]
        self.turn = 0 # com turn
        self.sub_turn = 0 # simulation frame

    @property
    def clients(self):
        return self.game_session.humans

    def get_client_by_login(self, login):
        for c in self.clients:
            if c.login == login:
                return c

    # communications with the client game interface

    def com_turn(self):
        return self.sub_turn == 0

    delay = 0

    def orders_are_ready(self):
        return not self.com_turn() or self.all_orders

    def write_line(self, s):
        self.orders += s + "\n"

    def _dispatch_orders(self):
        if self.world is None:
            self.world = self.clients[0].player.world
        if self.com_turn():
            self.main_server.write_line(
                 " ".join(map(str,
                    ("orders",
                    _pack(self.orders),
                    self.get_digest(),
                    chrono.value("ping"),
                    chrono.value("update"),
                    self.delay,
                    self.interface.real_speed)
                 ))
                )
            self.orders = ""
            chrono.start("ping")
            self._give_all_orders()
            self.turn += 1
        self.sub_turn += 1
        self.sub_turn %= self.fpct

    # communications with the world

    def get_digest(self):
        return "%s-%s.%s-%s" % (self.world.time,
                                self.turn, self.sub_turn,
                                md5(self.world.previous_state[1]).hexdigest())

    def get_sync_debug_msg_1(self):
        return "out_of_sync_error: map=%s version=%s platform=%s python=%s md5=%s time=%s" % (
            self.world.map.get_name(), VERSION, platform.platform(), sys.version.replace("\n", " "),
            self.get_digest(), self.world.previous_state[0])

    def get_sync_debug_msg_2(self):
        return "out_of_sync_error:debug_info orders=%s objects=%s" % (
               self._all_orders,
               self.world.previous_state[1][-150:],
               )

    def _give_all_orders(self):
        self._previous_update = time.time()
        all_orders = self.all_orders.pop(0)
        self.fpct = int(all_orders[0])
        players_orders = all_orders[1:]
        for player_orders in players_orders:
            player, orders = player_orders.split("/")
            direct_player = self.get_client_by_login(player).player
            if direct_player:
                orders = _unpack(orders)
                for order in orders.split("\n"):
                    if order:
                        self.queue_command(direct_player, order)
                if not order.startswith("control"):
                    self._all_orders += order.replace("order 0 0 ", "") + ";"
                    self._all_orders = self._all_orders[-100:]

    def update(self):
        s = self.main_server.read_line()
        if s is not None:
            args = s.split()
            if args[0] == "pong":
                chrono.stop("ping")
            elif args[0] == "all_orders":
                self.all_orders.append(args[1:])
                self.delay = time.time() - self.interface.next_update
            elif args[0] == "synchronization_error":
                if IS_DEV_VERSION:
                    open("user/tmp/%s-%s.txt" % (
                        self.world.previous_state[0],
                        md5(self.world.previous_state[1]).hexdigest()),
                         "w").write(self.world.previous_state[1])
                    open("user/tmp/%s-%s.txt" % (
                        self.world.previous_previous_state[0],
                        md5(self.world.previous_previous_state[1]).hexdigest()),
                         "w").write(self.world.previous_previous_state[1])
                else:
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
