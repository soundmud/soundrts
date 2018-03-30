import os.path
import random
import time

import config
import options
from constants import NEWLINE_REPLACEMENT, SPACE_REPLACEMENT, VIRTUAL_TIME_INTERVAL
from definitions import Style
from lib.log import debug, info, warning
from lib.msgs import nb2msg
import msgparts as mp
from paths import TMP_PATH
import res

import version
DEBUG_MODE = version.IS_DEV_VERSION


def insert_silences(msg):
    new_msg = []
    for sound in msg:
        new_msg.append(sound)
        new_msg += mp.PERIOD
    return new_msg


class _State(object):

    def send_menu(self, client):
        pass


class Anonymous(_State):

    allowed_commands = ("login", )


class InTheLobby(_State):

    allowed_commands = ("create", "register", "quit", "say")

    def send_menu(self, client):
        client.send_maps()
        client.send_invitations()
        client.push("update_menu\n")


class OrganizingAGame(_State):

    allowed_commands = ("invite", "invite_easy", "invite_aggressive",
                        "move_to_alliance",
                        "start", "cancel_game", "say",
                        "faction")

    def send_menu(self, client):
        client.push("available_players %s\n" % " ".join(
            [p.login for p in client.server.available_players(client)
             if p not in client.game.guests]))
        client.push("registered_players %s\n" % " ".join(["%s,%s,%s" % (p.login, p.alliance, p.faction) for p in client.game.players]))
        client.push("update_menu\n")


class WaitingForTheGameToStart(_State):

    allowed_commands = ("unregister", "say", "faction")

    def send_menu(self, client):
        client.push("registered_players %s\n" % " ".join(["%s,%s,%s" % (p.login, p.alliance, p.faction) for p in client.game.players]))
        client.push("update_menu\n")


class Playing(_State):

    allowed_commands = ("orders", "quit_game", "abort_game", "timeout", "debug_info",
                        "say")


class _Computer(object):

    login = "ai"

    def __init__(self, level):
        self.level = level

    def login_to_send(self):
        return self.login + "_" + self.level

    def push(self, msg):
        pass

    def send_msg(self, l):
        pass

    def send_menu(self):
        pass

    def is_compatible(self, client):
        return True

class Game(object):

    started = False
    speed = 1

    def __init__(self, scenario, speed, server, admin, is_public=False):
        self.id = server.get_next_id()
        self.scenario = scenario
        self.speed = speed
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

    def _delay(self):
        max_delay = max([p.delay for p in self.human_players])
        if max_delay > .6:
            info("max_delay=%s => max_delay=.6")
            max_delay = .6
        turn_duration = VIRTUAL_TIME_INTERVAL / 1000.0 / float(self.speed)
        nb_turns = int(max_delay / turn_duration) + 1
        info("max_delay=%s turn_duration=%s => %s buffered turns", max_delay,
             turn_duration, nb_turns)
        return nb_turns

    def _start(self):
        if options.record_games:
            self.f = open(os.path.join(TMP_PATH, "game%s-%s.txt" % (self.id, int(time.time()))), "w")
        info("start game %s on map %s with players %s",
             self.id,
             self.scenario.get_name(),
             " ".join([p.login_to_send() for p in self.players]))
        self.guests = []
        self.started = True
        self.human_players = [p for p in self.players if not isinstance(p, _Computer)]
        self.time = 0
        random.seed()
        seed = random.randint(0, 10000)
        # init self.all_orders
        self.all_orders = {}
        for client in self.human_players:
            self.all_orders[client] = []
        # send first orders (if menu, the advance in the delay isn't lost)
        delay = self._delay()
        for client in self.human_players:
            client.push("start_game %s %s %s %s\n" %
                        (";".join(["%s,%s,%s" % (p.login_to_send(), p.alliance,
                                                 p.faction)
                                   for p in self.players]),
                         client.login,
                         seed,
                         self.speed,
                         )
                        )
            for _ in range(delay):
                self.orders(client, ["update" + NEWLINE_REPLACEMENT, None])
            client.state = Playing()
        if options.record_games:
            self.f.write("start_game %s %s %s\n" %
                        (";".join(["%s,%s" % (p.login_to_send(), p.alliance)
                                   for p in self.players]),
                         seed,
                         self.scenario.get_name(),
                         )
                        )
        self.players = [] # remove the players from the registered players list
        self.server.log_status()

    def start(self):
        if self.scenario.nb_players_min <= len(self.players) <= self.scenario.nb_players_max:
            self._start()
        else:
            debug("couldn't start game: bad number of players")

    def quit_game(self, client): # called by a client already out of the game interface
        info("%s has quit from game %s after %s turns", client.login, self.id, self.time)
        self.human_players.remove(client)
        client.state = InTheLobby()
        if self.human_players:
            # remove the queue, and update the orders
            del self.all_orders[client]
            self._dispatch_orders_if_needed()
        else:
            self.close()

    def abort_game(self, client): # called by a client already out of the game interface
        info("%s has disconnected from game %s after %s turns", client.login, self.id, self.time)
        self.human_players.remove(client)
        client.state = InTheLobby() # useful if the client just aborted a game but has not disconnected
        if self.human_players:
            # give the last order for the other players
            for p in self.human_players:
                self.all_orders[p].insert(0, ["update" + NEWLINE_REPLACEMENT, None])
            self.all_orders[client].insert(0, ["quit" + NEWLINE_REPLACEMENT, None])
            self._dispatch_orders_if_needed()
            # remove the queue, and update the orders
            del self.all_orders[client]
            self._dispatch_orders_if_needed()
        else:
            self.close()

    def get_nb_minutes(self):
        return self.time * VIRTUAL_TIME_INTERVAL / 1000.0 / 60.0

    def get_status_msg(self):
        return mp.MULTIPLAYER + self.scenario.title + mp.PERIOD \
               + insert_silences([p.login for p in self.human_players]) + mp.PERIOD \
               + nb2msg(self.get_nb_minutes()) + mp.MINUTES

    def close(self):
        info("closed game %s after %s turns (played for %s minutes)", self.id,
             self.time, self.get_nb_minutes())
        self.cancel()
        self.server.log_status()
        if options.record_games:
            self.f.close()

    _nb_allowed_alerts = 1

    def _process_check_strings(self):
        check_strings = [queue[0][1] for queue in self.all_orders.values()]
        if check_strings.count(check_strings[0]) != len(check_strings) \
            and self._nb_allowed_alerts > 0:
            time_strings = [s.split("-", 1) for s in check_strings]
            if time_strings.count(time_strings[0]) != len(time_strings):
                if DEBUG_MODE:
                    info("minor mismatch in game %s at %s", self.id, self.time)
                return
            warning("mismatch in game %s at %s: %s",
                    self.id, self.time, check_strings)
            self._nb_allowed_alerts -= 1
            for p in self.human_players:
                if not p.is_disconnected:
                    p.push("synchronization_error\n")
        if "None" in check_strings:
            warning("check string for game %s == 'None'", self.id)

    def orders(self, client, args):
        self.all_orders[client].append(args)
        self._dispatch_orders_if_needed()

    def _orders_are_ready(self):
        for queue in self.all_orders.values():
            if not queue:
                return False
        return True

    def _dispatch_orders_if_needed(self):
        debug("dispatch orders if needed")
        while self._orders_are_ready():
            log_this = False
            debug(">> orders are ready")
            self._process_check_strings()
            # remove orders from the queue and pack them
            _all_orders = []
            for player, queue in self.all_orders.items():
                orders = queue.pop(0)[0]
                if SPACE_REPLACEMENT in orders:
                    log_this = True
                _all_orders.append("%s/%s" % (player.login, orders))
            all_orders = " ".join(_all_orders)
            # send orders
            for p in self.human_players:
                if not p.is_disconnected:
                    debug("send all_orders to %s", p.login)
                    p.push("all_orders %s\n" % all_orders)
                else:
                    debug("don't send all_orders to %s", p.login)
            if log_this and options.record_games:
                self.f.write("%s: all_orders %s\n" % (self.time, all_orders.replace(NEWLINE_REPLACEMENT, ";").replace(SPACE_REPLACEMENT, ",").replace("update;", 
"")))
            self.time += 1
            self._timeout_reference = None

    def invite(self, client):
        self.guests.append(client)
        client.send_msg([self.admin.login] + mp.INVITES_YOU + self.scenario.title)

    def invite_computer(self, level):
        if "admin_only" in self.server.parameters or \
           len(self.players) > 1: # at least two human players if public server
            self.register(_Computer(level))
        else:
            self.admin.send_msg(mp.BEEP)

    def uninvite(self, client):
        self.guests.remove(client)

    def move_to_alliance(self, player_index, alliance):
        player = self.players[int(player_index)]
        player.alliance = int(alliance)
        self.broadcast(mp.MOVE + [player.login] + mp.TO_ALLIANCE + nb2msg(player.alliance))

    def set_faction(self, player_index, faction):
        player = self.players[int(player_index)]
        player.faction = faction
        style = Style()
        style.load(res.get_text_file("ui/style", append=True, localize=True))
        faction_name = style.get(player.faction, 'title')
        self.broadcast([player.login, ] + faction_name)

    def broadcast(self, msg):
        for client in self.players:
            client.send_msg(msg)

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
            self.broadcast([client.login] + mp.HAS_JUST_JOINED + self.status())

    def status(self):
        assert not self.started
        msg = nb2msg(len(self.players)) + mp.PLAYERS_ON + nb2msg(self.scenario.nb_players_max)
        if len(self.players) >= self.scenario.nb_players_min:
            msg += mp.THE_GAME_WILL_START_WHEN_ORGANIZER_IS_READY
        else:
            msg += mp.NOT_ENOUGH_PLAYERS + nb2msg(self.scenario.nb_players_min)
        msg += mp.PERIOD + insert_silences([p.login for p in self.players])
        return msg

    def unregister(self, client):
        self.players.remove(client)
        if not client.is_disconnected:
            client.push("quit\n")
        client.state = InTheLobby()

    def cancel(self):
        for c in self.players[:]:
            self.unregister(c)
        for c in self.guests[:]:
            self.uninvite(c)
        self.server.games.remove(self)

    _timeout_reference = None

    def check_timeout(self):
        if self._timeout_reference is None:
            self._timeout_reference = time.time()
        elif time.time() > self._timeout_reference + config.timeout:
            for player, queue in self.all_orders.items():
                if not queue:
                    player.handle_close() # disconnect player
                    break # don't continue! (might disconnect more players)
