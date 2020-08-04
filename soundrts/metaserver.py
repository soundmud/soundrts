import os.path
import urllib.parse
import urllib.request
from typing import List

from .lib.log import warning
from . import msgparts as mp
from .paths import TMP_PATH
from .version import SERVER_COMPATIBILITY

# old value used by some features (stats, ...)
METASERVER_URL = "http://jlpo.free.fr/soundrts/metaserver/"

MAIN_METASERVER_URL = open("cfg/metaserver.txt").read().strip()
DEFAULT_SERVERS_PATH = "cfg/default_servers.txt"
RECENT_SERVERS_PATH = os.path.join(TMP_PATH, "recent_servers.txt")


def _add_time_and_version(line):
    words = line.split()
    words = ["0"] + words[:1] + [SERVER_COMPATIBILITY] + words[1:]
    return " ".join(words)


def _default_servers():
    lines = open(DEFAULT_SERVERS_PATH).readlines()
    return [_add_time_and_version(line) for line in lines
            if line.strip() and not line.startswith(";")]


def servers_list(voice) -> List[str]:
    # The header is an arbitrary string that the metaserver will include
    # in the reply to make sure that the PHP script is executed.
    header = "SERVERS"
    query = "header=%s&include_ports=1" % header
    servers_url = MAIN_METASERVER_URL + "servers.php?" + query
    try:
        f = urllib.request.urlopen(servers_url)
        if f.read(len(header)).decode() == header:
            s = f.read().decode()
            servers = s.split("\n")
            try:
                with open(RECENT_SERVERS_PATH, "w") as t:
                    t.write(s)
            except OSError:
                warning("couldn't save the list of servers")
        else:
            raise OSError(f"wrong header")
    except OSError as e:
        voice.alert(mp.BEEP + [str(e)])  # type: ignore
        warning(str(e))
        warning("couldn't get the servers list from the metaserver")
        try:
            with open(RECENT_SERVERS_PATH) as t:
                servers = t.read().split("\n")
            warning(f"using {RECENT_SERVERS_PATH} instead")
        except OSError:
            warning(f"couldn't read {RECENT_SERVERS_PATH}")
            warning(f"using {DEFAULT_SERVERS_PATH} instead")
            servers = _default_servers()
    return servers
