from soundrts.clientserver import ConnectionToServer


class Telnet:

    done = False

    def read_very_eager(self):
        if self.done:
            return b""
        else:
            self.done = True
            return b"0\n1\n2\n"


def test_read_line_chronological():
    c = ConnectionToServer(None, None)
    c.tn = Telnet()
    assert c.read_line() == "0"
    assert c.read_line() == "1"
    assert c.read_line() == "2"
    assert c.read_line() is None
    assert c.read_line() is None
    
