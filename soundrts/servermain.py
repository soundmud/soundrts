import asyncore
import re
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache

from . import config, discovery, options, paths
from .lib.log import debug, exception, info, warning
from .lib.ticker import Ticker
from .metaserver import MAIN_METASERVER_URL
from .serverclient import ConnectionToClient
from .serverroom import (
    Game,
    InTheLobby,
    OrganizingAGame,
    Playing,
    WaitingForTheGameToStart,
)
from .version import SERVER_COMPATIBILITY

REGISTER_INTERVAL = 10 * 60  # register server every 10 minutes
REGISTER_URL = MAIN_METASERVER_URL + "servers_register.php"
UNREGISTER_URL = MAIN_METASERVER_URL + "servers_unregister.php"
WHATISMYIP_URL = open("cfg/whatismyip.txt").read().strip()


@lru_cache()
def _public_ip():
    if options.ip:
        warning(f"using the public IP address specified in the options: {options.ip}")
        return options.ip
    try:
        ip = (
            urllib.request.urlopen(WHATISMYIP_URL, timeout=3)
            .read()
            .decode("ascii")
            .strip()
        )
        if not re.match("^[0-9.]{7,40}$", ip):
            ip = ""
    except:
        ip = ""
    if not ip:
        warning("could not get public IP address from %s", WHATISMYIP_URL)
    else:
        info(f"public IP address is {ip}")
    return ip


@lru_cache()
def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 1))
        return s.getsockname()[0]
    except:
        warning("couldn't get the local IP")


@lru_cache()
def _upnp_router():
    import upnpclient

    for device in upnpclient.discover():
        if hasattr(device, "WANIPConn1") and hasattr(
            device.WANIPConn1, "AddPortMapping"
        ):
            return device.WANIPConn1


_upnp_failed = False


def _forward_port():
    global _upnp_failed
    if _upnp_failed:
        return
    try:
        _upnp_router().AddPortMapping(
            NewRemoteHost="",
            NewExternalPort=options.port,
            NewProtocol="TCP",
            NewInternalPort=options.port,
            NewInternalClient=_local_ip(),
            NewEnabled="1",
            NewPortMappingDescription="SoundRTS",
            NewLeaseDuration=REGISTER_INTERVAL * 2,
        )
    except:
        _upnp_failed = True
        warning(
            f"couldn't forward port {options.port} (TCP) to local IP using UPnP IGD"
        )
        warning("you might have to configure your router manually")
    else:
        info(
            f"port {options.port} (TCP) forwarded to {_local_ip()}:{options.port} for {REGISTER_INTERVAL * 2} seconds"
        )


class Server(asyncore.dispatcher):
    def __init__(self, parameters, is_standalone):
        self.parameters = parameters
        self.is_standalone = is_standalone
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(("", options.port))
        self.listen(5)
        self.login = config.login
        self.clients = []
        self.games = []
        if "admin_only" in parameters:
            self.nb_games_max = 1
            self.nb_clients_max = 20
        else:
            self.nb_games_max = 10
            self.nb_clients_max = 40

    next_id = 0

    def get_next_id(self, increment=True):
        if increment:
            self.next_id += 1
            return self.next_id
        else:
            return self.next_id + 1

    def handle_connect(self):
        pass

    def handle_read(self):
        pass

    def handle_accept(self):
        ConnectionToClient(self, self.accept())

    def _cleanup(self):
        for c in self.clients[:]:
            if c not in list(asyncore.socket_map.values()):
                self.clients.remove(c)
        if self.games and not self.clients:
            self.games = []

    def log_status(self):
        self._cleanup()
        info(
            "%s players (%s not playing), %s games",
            len(self.clients),
            len(self.players_not_playing()),
            len([g for g in self.games if g.started]),
        )

    def _is_admin(self, client):
        return client.address[0] == "127.0.0.1" and client.login == self.login

    def remove_client(self, client):
        client.is_disconnected = True
        must_log = False
        if client in self.clients:  # not anonymous
            must_log = True
            info("disconnect: %s" % client.login)
            self.clients.remove(client)
            for c in self.players_not_playing():
                if client.is_compatible(c):
                    c.notify("logged_out", client.login)
            self.update_menus()
        if isinstance(client.state, Playing):
            client.cmd_quit_game([])
        elif isinstance(client.state, WaitingForTheGameToStart):
            client.cmd_unregister([])
        elif isinstance(client.state, OrganizingAGame):
            client.cmd_cancel_game([])
        if self._is_admin(client) and not self.is_standalone:
            info("the admin has disconnected => close the server")
            sys.exit()
        if must_log:
            self.log_status()

    def handle_write(self):
        pass

    def handle_close(self):
        try:
            debug("Server.handle_close")
        except:
            pass
        sys.exit()

    def handle_error(self):
        try:
            debug("Server.handle_error %s", sys.exc_info()[0])
        except:
            pass
        if sys.exc_info()[0] in [SystemExit, KeyboardInterrupt]:
            sys.exit()
        else:
            try:
                exception("Server.handle_error")
            except:
                pass

    def can_create(self, client):
        if "admin_only" in self.parameters:
            return self._is_admin(client)
        else:
            return len([g for g in self.games if g.started]) < self.nb_games_max

    def unregister(self):
        try:
            info("unregistering server...")
            s = urllib.request.urlopen(UNREGISTER_URL + "?ip=" + _public_ip()).read()
        except:
            s = "couldn't access to the metaserver"
        if s:
            warning("couldn't unregister from the metaserver (%s)", s[:80])

    def _register(self):
        try:
            s = urllib.request.urlopen(
                REGISTER_URL
                + "?version=%s&login=%s&ip=%s&port=%s"
                % (SERVER_COMPATIBILITY, self.login, _public_ip(), options.port)
            ).read()
        except:
            s = "couldn't access to the metaserver"
        if s:
            warning("couldn't register to the metaserver (%s)", s[:80])
        else:
            info("server registered")

    def register(self):
        _forward_port()
        self._register()

    def _start_registering(self):
        self.ticker = Ticker(REGISTER_INTERVAL, self.register)
        self.ticker.start()

    def startup(self):
        if "no_metaserver" not in self.parameters:
            self._start_registering()
        threading.Thread(
            target=discovery.server_loop,
            args=(f"{SERVER_COMPATIBILITY} {options.port} {self.login}",),
            daemon=True,
        ).start()
        info("server started")
        info('user folder is "%s"', paths.CONFIG_DIR_PATH)
        info('configuration file is "%s"', paths.CONFIG_FILE_PATH)
        info('from SoundRTS.ini: login is "%s" (server name)', config.login)
        asyncore.loop()

    def update_menus(self):
        for c in self.clients:
            c.send_menu()

    def available_players(self, client=None):
        lst = []
        for x in self.clients:
            if isinstance(x.state, InTheLobby):
                if client:
                    if x.is_compatible(client):
                        lst.append(x)
                else:
                    lst.append(x)
        return lst

    def game_admins(self):
        return [x for x in self.clients if isinstance(x.state, OrganizingAGame)]

    def players_not_playing(self):
        return [x for x in self.clients if not isinstance(x.state, Playing)]

    def get_client_by_login(self, login):
        for c in self.clients:
            if c.login == login:
                return c

    def get_game_by_id(self, ident) -> Game:
        ident = int(ident)
        for o in self.games:
            if o.id == ident:
                return o
        assert False


def start_server(parameters=sys.argv, is_standalone=True):
    try:
        server = Server(parameters, is_standalone)
        server.startup()
    finally:
        try:
            info("closing server...")
            if hasattr(server, "ticker"):
                server.ticker.cancel()
            server.unregister()
            # make sure channels are closed (useful?)
            for c in server.clients:
                c.close()
            server.close()
        except:
            exception("couldn't close the server")


def main():
    while config.login == config.DEFAULT_LOGIN:
        login = input("Please enter the name of the server: ")
        if config.login_is_valid(login):
            config.login = login
            config.save()
        else:
            print("Please use only ASCII letters and digits (no space).")
    print("Starting the server in standalone mode...")
    print("To stop the server, press Ctrl+C on Linux, Ctrl+Break on Windows.")
    start_server()
