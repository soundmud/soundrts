try:
    from ctypes import *
except:
    pass
import platform
import os
import os.path
import urllib
##try:
##    import wmi
##except:
##    info("can't import wmi")

from lib.log import *


class Stats(object):

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
                for game_type in stats.keys():
                    nb_games, total_duration = stats[game_type]
                    f.write(" ".join((game_type, repr(nb_games), repr(total_duration))) + "\n")
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
                if stats.has_key(game_type):
                    stats[game_type][0] += 1
                    stats[game_type][1] += duration
                else:
                    stats[game_type] = [1, duration]
                self._write_file(stats)
        except:
            debug("error adding stats")

    def get(self, game_type): # used for unit test
        stats = self._read_file()
        if stats.has_key(game_type):
            return tuple(stats[game_type])
        else:
            return None

    def send(self):
        try:
            stats = self._read_file()
            weak_id = self._get_weak_user_id()
            for game_type in stats.keys():
                nb_games, total_duration = stats[game_type]
                try:
                    s = urllib.urlopen(self.server + "stats.php?method=add&game_type=%s&nb_games=%s&total_duration=%s&weak_id=%s" % (game_type, nb_games, total_duration, weak_id)).read()
                except:
                    debug("stats server didn't reply")
                    break # don't try next stats
                if  s == "":
                    del stats[game_type]
                    self._write_file(stats)
                else:
                    debug("wrong reply from the stats server (stats will be sent again next time): %s", s)
            self._write_file(stats) # remove file if empty
        except:
            debug("error sending stats")

    def _get_weak_user_id(self):
        # truncated hash of various parameters
        # used to approximate the number of users, not more
##        try:
##            processor_id = wmi.WMI().Win32_Processor()[0].ProcessorId
##        except:
##            info("can't get processor id")
##            processor_id = "unknown"
##        platform_uname = repr(platform.uname()) # can change over time (but not too often)
##        volume_id = repr(_get_volume_serial_number())
##        thing_to_hash = processor_id + volume_id + platform_uname
        thing_to_hash = self._get_volume_serial_number()
        user_id = "%s" % abs(hash(thing_to_hash))
        user_id = user_id[:4] # collisions are probable
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
            windll.kernel32.GetVolumeInformationA( \
                lpRootPathName, \
                lpVolumeNameBuffer, nVolumeNameSize, \
                byref(lpVolumeSerialNumber), \
                byref(lpMaximumComponentLength),
                byref(lpFileSystemFlags), \
                lpFileSystemNameBuffer, nFileSystemNameSize)
            return lpVolumeSerialNumber.value
        except:
            debug("can't get volume serial number") # Mac, Linux
            return 0
