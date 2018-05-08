import socket
import sys
import telnetlib
import threading
import time

from clientmedia import voice
from clientservermenu import ServerMenu
from clientversion import revision_checker
import config
import options
from lib.log import info, exception
import msgparts as mp
import servermain
from version import compatibility_version


class _Error(Exception): pass
class UnreachableServerError(_Error): pass
class WrongServerError(_Error): pass
class CompatibilityOrLoginError(_Error): pass
class ConnectionAbortedError(_Error): pass


class ServerInAThread(threading.Thread):

    daemon = True

    def __init__(self, parameters):
        threading.Thread.__init__(self)
        self.parameters = parameters

    def run(self):
        servermain.start_server(self.parameters, is_standalone=False)


def start_server_and_connect(parameters):
    info("active threads: %s", threading.enumerate())
    ServerInAThread(parameters).start()
    time.sleep(.01) # Linux needs a small delay (at least on the Eee PC 4G)
    revision_checker.start_if_needed()
    connect_and_play()
    info("active threads: %s", threading.enumerate())
    sys.exit()

def connect_and_play(host="127.0.0.1", port=options.port, auto=False):
    try:
        server = ConnectionToServer(host, port)
        ServerMenu(server, auto=auto).loop()
        server.close() # without this, the server isn't closed after a game
    except UnreachableServerError:
        voice.alert(mp.SERVER_UNREACHABLE)
    except WrongServerError:
        voice.alert(mp.UNEXPECTED_REPLY + [compatibility_version()])
    except CompatibilityOrLoginError:
        voice.alert(mp.CONNECTION_REJECTED + [compatibility_version()] + mp.OR_LOGIN_REJECTED)
    except ConnectionAbortedError:
        voice.alert(mp.CONNECTION_INTERRUPTED)
    except SystemExit:
        raise
    except:
        voice.alert(mp.ERROR_DURING_CONNECTION)
        exception("error during connection to server")


class ConnectionToServer(object):

    data = ""
    tn = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        if host is not None:
            self.open()

    def open(self):
        try:
            self.tn = telnetlib.Telnet(self.host, self.port)
        except socket.error:
            raise UnreachableServerError
        try:
            if self.tn.read_until(":", 3) != ":":
                raise WrongServerError
            self.tn.write("login " + compatibility_version() + " %s\n" % config.login)
        except (EOFError, socket.error):
            raise WrongServerError
        try:
            self.tn.read_until("ok!", 5)
        except EOFError:
            raise CompatibilityOrLoginError

    def close(self):
        self.tn.close()

    def read_line(self):
        try:
            self.data += self.tn.read_very_eager()
        except: # EOFError or (10054, 'Connection reset by peer')
            raise ConnectionAbortedError
        if "\n" in self.data:
            line, self.data = self.data.split("\n", 1)
            return line

    def write_line(self, s):
        try:
            self.tn.write(s + "\n")
        except socket.error: # connection aborted
            raise ConnectionAbortedError
