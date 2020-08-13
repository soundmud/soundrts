from soundrts.serverclient import ConnectionToClient


class Client(ConnectionToClient):
    def __init__(self):
        self.inbuffer = b""

    def _execute_command(self, data):
        self.cmd = data


class Server:

    clients = []  # type: ignore


def test_found_terminator():
    c = Client()
    c.collect_incoming_data(b"0")
    c.found_terminator()
    assert c.cmd == b"0"


def test_unique_login():
    c = Client()
    c.server = Server()
    assert c._unique_login("ai_easy") == "player"
    assert c._unique_login("name") == "name"
    c2 = Client()
    c2.login = "name"
    c.server.clients = [c2]
    assert c._unique_login("name") == "name2"
    c3 = Client()
    c3.login = "name2"
    c.server.clients = [c2, c3]
    assert c._unique_login("name") == "name3"
