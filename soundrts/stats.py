try:
    from ctypes import byref, c_ulong, create_string_buffer, sizeof, windll
except:
    pass
import os
import urllib.error
import urllib.parse
import urllib.request

from .lib.log import debug
from .metaserver import METASERVER_URL
from .paths import STATS_PATH


class Stats:
    def __init__(self, filepath, server):
        self.filepath = filepath
        self.server = server

    def _read_file(self):
        if os.path.exists(self.filepath):
            lines = open(self.filepath).readlines()
        else:
            lines = []
        stats = {}
        for line in lines:
            try:
                game_type, nb_games, total_duration = line.split()
                stats[game_type] = [int(nb_games), int(total_duration)]
            except:
                debug("stat ignored: %s", line)
        return stats

    def _write_file(self, stats):
        if stats:
            try:
                f = open(self.filepath, "w")
                for game_type in list(stats.keys()):
                    nb_games, total_duration = stats[game_type]
                    f.write(
                        " ".join((game_type, repr(nb_games), repr(total_duration)))
                        + "\n"
                    )
                f.close()
            except:
                debug("stats lost")
        elif os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
            except:
                debug("couldn't remove empty stats file")

    def add(self, game_type, duration):
        try:
            if duration >= 60:
                stats = self._read_file()
                if game_type in stats:
                    stats[game_type][0] += 1
                    stats[game_type][1] += duration
                else:
                    stats[game_type] = [1, duration]
                self._write_file(stats)
        except:
            debug("error adding stats")

    def get(self, game_type):  # used for unit test
        stats = self._read_file()
        if game_type in stats:
            return tuple(stats[game_type])
        else:
            return None

    def send(self):
        try:
            stats = self._read_file()
            weak_id = self._get_weak_user_id()
            for game_type in list(stats.keys()):
                nb_games, total_duration = stats[game_type]
                try:
                    s = urllib.request.urlopen(
                        self.server
                        + f"stats.php?method=add&game_type={game_type}&nb_games={nb_games}&total_duration={total_duration}&weak_id={weak_id}"
                    ).read()
                except:
                    debug("stats server didn't reply")
                    break  # don't try next stats
                if s == "":
                    del stats[game_type]
                    self._write_file(stats)
                else:
                    debug(
                        "wrong reply from the stats server (stats will be sent again next time): %s",
                        s,
                    )
            self._write_file(stats)  # remove file if empty
        except:
            debug("error sending stats")

    def _get_weak_user_id(self):
        # truncated hash of various parameters
        # used to approximate the number of users, not more
        thing_to_hash = self._get_volume_serial_number()
        user_id = "%s" % abs(hash(thing_to_hash))
        user_id = user_id[:4]  # collisions are probable
        debug("user id = %s" % user_id)
        return user_id

    def _get_volume_serial_number(self):
        # Reference: http://msdn2.microsoft.com/en-us/library/aa364993.aspx
        try:
            lpRootPathName = "c:\\"
            lpVolumeNameBuffer = create_string_buffer(1024)
            nVolumeNameSize = sizeof(lpVolumeNameBuffer)
            lpVolumeSerialNumber = c_ulong()
            lpMaximumComponentLength = c_ulong()
            lpFileSystemFlags = c_ulong()
            lpFileSystemNameBuffer = create_string_buffer(1024)
            nFileSystemNameSize = sizeof(lpFileSystemNameBuffer)
            windll.kernel32.GetVolumeInformationA(  # @UndefinedVariable
                lpRootPathName,
                lpVolumeNameBuffer,
                nVolumeNameSize,
                byref(lpVolumeSerialNumber),
                byref(lpMaximumComponentLength),
                byref(lpFileSystemFlags),
                lpFileSystemNameBuffer,
                nFileSystemNameSize,
            )
            return lpVolumeSerialNumber.value
        except:
            debug("can't get volume serial number")  # Mac, Linux
            return 0


_stats = Stats(STATS_PATH, METASERVER_URL)
add = _stats.add
