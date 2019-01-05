import urllib2

import msgparts as mp


# old value used by some features (stats, ...)
METASERVER_URL = "http://jlpo.free.fr/soundrts/metaserver/"

MAIN_METASERVER_URL = open("cfg/metaserver.txt").read().strip()

def _add_time_and_version(line):
    words = line.split()
    words = ["0"] + words[:1] + [VERSION] + words[1:]
    return " ".join(words)

def _default_servers():
    lines = open("cfg/default_servers.txt").readlines()
    return [_add_time_and_version(line) for line in lines
            if line.strip() and not line.startswith(";")]

def servers_list(voice):
    # The header is an arbitrary string that the metaserver will include
    # in the reply to make sure that the PHP script is executed.
    header = "SERVERS"
    query = "header=%s&include_ports=1" % header
    servers_url = MAIN_METASERVER_URL + "servers.php?" + query
    try:
        f = urllib2.urlopen(servers_url)
        if f.read(len(header)) == header:
            servers = f.readlines()
    except:
        voice.alert(mp.BEEP)
        warning("couldn't get the servers list from the metaserver"
                " => using the default servers list")
        servers = _default_servers()
    return servers
