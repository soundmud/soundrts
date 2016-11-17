"""command line options"""

import optparse

from lib.log import warning


ip = None
mods = None
port = 2500
record_games = False


def _parse_options():
    global ip, mods, port, record_games
    default_port = port
    parser = optparse.OptionParser()
    parser.add_option("-i", "--ip", type="string")
    parser.add_option("-m", "--mods", type="string")
    parser.add_option("-p", type="int", help=optparse.SUPPRESS_HELP)
    parser.add_option("-g", action="store_true", help=optparse.SUPPRESS_HELP)
    parser.set_defaults(ip=None, mods=None, p=default_port, g=False)
    options, _ = parser.parse_args()
    ip = options.ip
    mods = options.mods
    port = options.p
    record_games = options.g
    if ip:
        warning("using IP %s", ip)
    if port != default_port:
        warning("using port %s (instead of %s)", port, default_port)
    if record_games:
        warning("games will be recorded on the server")


_parse_options()
