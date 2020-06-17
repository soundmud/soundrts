import random
import time

from . import config
from .definitions import VIRTUAL_TIME_INTERVAL
from .lib.log import info, warning
from .version import IS_DEV_VERSION


def same(strings):
    return len(set(strings)) == 1

def time_string(check_string):
    if check_string is not None:
        return check_string.split("-", 1)[0]

def pack(p):
    return ",".join((p.login, str(p.alliance), p.faction))


class _State:

    def send_menu(self, client):
        pass


class Anonymous(_State):

    allowed_commands = ("login", )


class InTheLobby(_State):

    allowed_commands = ("create", "register", "quit", "say")

    def send_menu(self, client):
        client.send_maps()
        client.send_invitations()
        client.notify("update_menu")


class OrganizingAGame(_State):

    allowed_commands = ("invite", "invite_easy", "invite_aggressive", "invite_ai2",
                        "move_to_alliance",
                        "start", "cancel_game", "say",
                        "faction")

    def send_menu(self, client):
        client.notify(
            "available_players",
            *[p.login for p in client.server.available_players(client)
              if p not in client.game.guests])
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class WaitingForTheGameToStart(_State):

    allowed_commands = ("unregister", "say", "faction")

    def send_menu(self, client):
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class Playing(_State):

    allowed_commands = ("orders", "quit_game", "timeout", "debug_info", "say")


class _Computer:

    def __init__(self, level):
        self.level = level

    @property
    def login(self):
        return "ai_" + self.level


class Orders:

    def __init__(self, game):
        self.all_orders = {}
        for client in game.human_players:
            self.all_orders[client] = []

    def __repr__(self):
        return "<Orders '%s'>" % repr(self.all_orders)

    def add(self, client, args):
        self.all_orders[client].append(args)

    def pop_and_pack(self):
        _all_orders = []
        for player, queue in list(self.all_orders.items()):
            orders = queue.pop(0)[0]
            _all_orders.append(f"{player.login}/{orders}")
        return " ".join(_all_orders)

    def are_ready(self):
        return [] not in list(self.all_orders.values())

    def remove(self, client):
        del self.all_orders[client]

    def players_without_orders(self):
        return [player for player, queue in list(self.all_orders.items()) if not queue]

    def get_next_check_strings(self):
        return [queue[0][1] for queue in list(self.all_orders.values())]


class Game:

    started = False
    speed = 1

    def __init__(self, scenario, speed, server, admin, is_public=False):
        self.id = server.get_next_id()
        self.scenario = scenario
        self.speed = speed
        self.real_speed = speed
        self.server = server
        self.admin = admin
        self.is_public = is_public
        self.players = []
        self.guests = []
        self.register(admin)
        if self.is_public:
            self._process_public_game()

    def _process_public_game(self):
        for player in self.server.available_players():
            if player.is_compatible(self.admin):
                self.invite(player)

    def notify_connection_of(self, client):
        if self.is_public and self.can_register() and client.is_compatible(self.admin):
            self.invite(client)

    @property
    def human_players(self):
        return [p for p in self.players if not isinstance(p, _Computer)]

    def _start(self):
        info("start game %s on map %s with players %s",
             self.id,
             self.scenario.get_name(),
             " ".join(p.login for p in self.players))
        self.guests = []
        self.started = True
        self.time = 0
        random.seed()
        seed = random.randint(0, 10000)
        self._orders = Orders(self)
##        # guess first ping from the connection delays
##        self.ping = max([p.delay for p in self.human_players])
        for client in self.human_players:
            client.notify(
                "start_game",
                ";".join(pack(p) for p in self.players),
                 client.login,
                 seed,
                 self.speed)
            client.state = Playing()
        self.server.log_status()
        self._start_time = time.time()

    def start(self):
        if self.scenario.nb_players_min <= len(self.players) <= self.scenario.nb_players_max:
            self._start()
        else:
            warning("couldn't start game: bad number of players")

    def remove(self, client):
        info("%s has quit game %s after %s turns", client.login, self.id, self.time)
        self.players.remove(client)
        if self.human_players:
            self._orders.remove(client)
            self._dispatch_orders_if_needed()
        else:
            self.close()

    @property
    def nb_minutes(self):
        return int((time.time() - self._start_time) / 60)

    def close(self):
        info("closed game %s after %s turns (played for %s minutes)", self.id,
             self.time, self.nb_minutes)
        self.cancel()
        self.server.log_status()

    _nb_allowed_alerts = 1

    def _check_synchronization(self, check_strings):
        if not same(check_strings) and self._nb_allowed_alerts > 0:
            if not same(time_string(cs) for cs in check_strings):
                if IS_DEV_VERSION and None not in check_strings:
                    info("time mismatch in game %s at turn %s: %s",
                         self.id, self.time, check_strings)
                return
            warning("mismatch in game %s at turn %s: %s",
                    self.id, self.time, check_strings)
            self._nb_allowed_alerts -= 1
            self.notify("synchronization_error")

    ping = 0
    delay = 0

    def orders(self, client, orders, check=None, ping=0, update=0, delay=0, real_speed=0):
        self.ping = max(self.ping, float(ping))
        self.delay = max(self.delay, float(delay))
        self.real_speed = min(self.real_speed, float(real_speed))
        self._orders.add(client, [orders, check])
        self._dispatch_orders_if_needed()

    max_ping = .5 # seconds

    def fpct(self):
        """number of simulation frames per communication turn"""
        # 1 is probably the best number in most cases because the game is often CPU-bound.
        # the following number could be chosen instead someday
        tps = self.real_speed * 1000 / VIRTUAL_TIME_INTERVAL
        # Avoid unrealistic ping values.
        ping = min(self.max_ping, self.ping)
        result = int(tps * ping * config.fpct_coef) + 1
        return min(config.fpct_max, result)

    def _dispatch_orders_if_needed(self):
        while self._orders.are_ready():
            self._check_synchronization(self._orders.get_next_check_strings())
            all_orders = self._orders.pop_and_pack()
            self.notify("all_orders", self.fpct(), all_orders)
            self.time += 1
            self._timeout_reference = None
            self.ping = 0
            self.delay = 0
            self.real_speed = self.speed

    def invite(self, client):
        self.guests.append(client)
        client.notify("invitation", self.admin.login, self.scenario.get_name()[:-4])

    def invite_computer(self, level):
        if not config.require_humans or \
           "admin_only" in self.server.parameters or \
           len(self.players) > 1:
            self.register(_Computer(level))
        else:
            self.admin.notify("invite_computer_error")

    def uninvite(self, client):
        self.guests.remove(client)

    def move_to_alliance(self, player_index, alliance):
        player = self.players[int(player_index)]
        player.alliance = int(alliance)
        self.notify("alliance", player.login, player.alliance)

    def set_faction(self, player_index, faction):
        player = self.players[int(player_index)]
        player.faction = faction
        self.notify("faction", player.login, faction)

    def notify(self, *args):
        for client in self.human_players:
            client.notify(*args)

    def can_register(self):
        return not self.started and len(self.players) < self.scenario.nb_players_max

    def register(self, client):
        if self.can_register():
            for n in range(len(self.players) + 1):
                n += 1
                if n not in [p.alliance for p in self.players]:
                    break
            self.players.append(client)
            client.game = self
            client.alliance = n
            client.faction = "random_faction"
            self.notify("registered", client.login, ",".join([c.login for c in self.players]))

    @property
    def short_status(self):
        return (self.scenario.get_name()[:-4],
                ",".join([c.login for c in self.players]),
                self.nb_minutes)

    def unregister(self, client):
        self.players.remove(client)
        client.notify("quit")
        client.state = InTheLobby()

    def cancel(self):
        for c in self.human_players:
            self.unregister(c)
        for c in self.guests[:]:
            self.uninvite(c)
        self.server.games.remove(self)

    _timeout_reference = None

    def check_timeout(self):
        if self._timeout_reference is None:
            self._timeout_reference = time.time()
        elif time.time() > self._timeout_reference + config.timeout:
            for player in self._orders.players_without_orders():
                warning("timeout %s", player.login)
                player.handle_close() # disconnect player
                break # don't continue! (might disconnect more players)
