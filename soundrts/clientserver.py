import os
import socket
import sys
import telnetlib
import threading
import time

from clientmedia import *
from clientservermenu import ServerMenu
from clientversion import *
from commun import *
import config
import servermain


class _Error(Exception): pass
class UnreachableServerError(_Error): pass
class WrongServerError(_Error): pass
class CompatibilityOrLoginError(_Error): pass
class ConnectionAbortedError(_Error): pass


class ServerInAThread(threading.Thread):

    def __init__(self, parameters):
        threading.Thread.__init__(self)
        self.parameters = parameters

    def run(self):
        servermain.start_server(self.parameters, is_standalone=False)


def start_server_and_connect(parameters):
    info("active threads: %s", threading.enumerate())
    ServerInAThread(parameters).start()
    # TODO: catch exceptions raised by the starting server
    # for example: RegisteringError ProbablyNoInternetError
    # voice.alert([4049]) # "The server couldn't probably register on the metaserver. check you are connected to the Internet."
    # voice.alert([4080]) # "failure: the server couldn't start"
    time.sleep(.01) # Linux needs a small delay (at least on the Eee PC 4G)
    revision_checker.start_if_needed()
    connect_and_play()
    info("active threads: %s", threading.enumerate())
    sys.exit()

def connect_and_play(host="127.0.0.1", port=config.port):
    try:
        server = ConnectionToServer(host, port)
        ServerMenu(server).loop()
        server.close() # without this, the server isn't closed after a game
    except UnreachableServerError:
        # "failure: the server unreachable. The server is closed or behind a firewall or behind a router."
        voice.alert([4081])
    except WrongServerError:
        # "failure: unexpected reply from the server. The server is not a SoundRTS server" (version)
        voice.alert([4082, COMPATIBILITY_VERSION])
    except CompatibilityOrLoginError:
        # "failure: connexion rejected the server. The server is not a SoundRTS server" (version)
        # "or your login has been rejected"
        voice.alert([4083, COMPATIBILITY_VERSION, 4084])
    except ConnectionAbortedError:
        voice.alert([4102]) # connection aborted
    except SystemExit:
        raise
    except:
        voice.alert([4085]) # "error during connexion to server"
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
            self.tn.write("login " + COMPATIBILITY_VERSION + " %s\n" % config.login)
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
        lines = self.data.split("\n", 1)
        self.data = lines.pop()
        if lines:
            return lines[0]

    def write_line(self, s):
        try:
            self.tn.write(s + "\n")
        except socket.error: # connection aborted
            raise ConnectionAbortedError
