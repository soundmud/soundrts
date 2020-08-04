import urllib.parse
import urllib.request
from typing import List

from .lib.log import warning
from . import msgparts as mp
from .version import SERVER_COMPATIBILITY

# old value used by some features (stats, ...)
METASERVER_URL = "http://jlpo.free.fr/soundrts/metaserver/"

MAIN_METASERVER_URL = open("cfg/metaserver.txt").read().strip()


def _add_time_and_version(line):
    words = line.split()
    words = ["0"] + words[:1] + [SERVER_COMPATIBILITY] + words[1:]
    return " ".join(words)


def _default_servers():
    lines = open("cfg/default_servers.txt").readlines()
    return [_add_time_and_version(line) for line in lines
            if line.strip() and not line.startswith(";")]


def servers_list(voice) -> List[str]:
    servers = _default_servers()
    # The header is an arbitrary string that the metaserver will include
    # in the reply to make sure that the PHP script is executed.
    header = "SERVERS"
    query = "header=%s&include_ports=1" % header
    servers_url = MAIN_METASERVER_URL + "servers.php?" + query
    try:
        f = urllib.request.urlopen(servers_url)
        if f.read(len(header)).decode() == header:
            servers = f.read().decode().split("\n")
        else:
            voice.alert(mp.BEEP)
            warning(f"the servers list from the metaserver doesn't start with {header}"
                    " => using the default servers list")
    except OSError as e:
        voice.alert(mp.BEEP + [str(e)])  # type: ignore
        warning(str(e))
        warning("couldn't get the servers list from the metaserver"
                " => using the default servers list")
    return servers
