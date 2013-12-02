import base64
try: 
    from hashlib import md5
except ImportError:
    from md5 import md5
import os.path
import re
import shutil

from config import *
from constants import *
from lib.log import *
from lib import zipdir
import world


class Map(object):

    map_string = None

    def __init__(self, p=None, digest="no_digest", official=False):
        self.mapfile = p
        self.digest = digest
        self.official = official
        if p:
            self._load_header()

    def _read_additional_file(self, n):
        p = os.path.join(self.mapfile, n)
        if os.path.isfile(p):
            return open(p, "U").read()
        else:
            return ""

    def _read_campaign_file(self, n):
        if getattr(self, "campaign", None) is None:
            return ""
        p = os.path.join(self.campaign.path, n)
        if os.path.isfile(p):
            return open(p, "U").read()
        else:
            return ""
        
    @property
    def additional_rules(self):
        return self._read_additional_file("rules.txt")

    @property
    def campaign_rules(self):
        return self._read_campaign_file("rules.txt")

    @property
    def additional_ai(self):
        return self._read_additional_file("ai.txt")

    @property
    def campaign_ai(self):
        return self._read_campaign_file("ai.txt")

    @property
    def additional_style(self):
        return self._read_additional_file(os.path.join("ui", "style.txt"))

    @property
    def campaign_style(self):
        return self._read_campaign_file(os.path.join("ui", "style.txt"))

    def get_additional(self, n):
        return self._read_additional_file(n)

    def get_campaign(self, n):
        return self._read_campaign_file(n)
        
    def get_name(self):
        try:
            return re.sub("[^A-Za-z0-9._-]", "",
                       os.path.split(self.mapfile)[-1])
        except:
            return "unknown"

    def read(self):
        if self.map_string is not None:
            return self.map_string
        elif os.path.isdir(self.mapfile):
            return open(os.path.join(self.mapfile, "map.txt"), "U").read()
        else:
            return open(self.mapfile, "U").read()

    def _extract_title(self, s):
        m = re.search("(?m)^title[ \t]+([0-9 ]+)$", s)
        if m and not self.official:
            self.title = [int(x) for x in m.group(1).split(" ")]
        else:
            name = os.path.split(self.mapfile)[1].lower()
            name = re.sub("\.txt$", "", name)
            name = re.sub("[^a-zA-Z0-9]", "", name)
            self.title = [name]

    def get_digest(self):
        # I use MD5 because:
        # 1. I am not sure if hash() gives the same result on different versions.
        # 2. MD5 is better as a hash than a simple CRC32 checksum.
        # 3. MD5 is secure enough (this protection can be removed easily anyway), so SHA1 is not needed here.
        try:
            s = self.read()
        except:
            s = ""
        s += self.additional_rules + self.additional_ai
        return md5(s).hexdigest()

    def _check_digest(self):
        if self.digest is None:
            self.title.insert(0, 1097) # heal sound to alert player
        elif self.digest != "no_digest" and self.get_digest() != self.digest:
            self.title.insert(0, 1029) # hostile sound to alert player
            debug("%s\n>>>%s<<<", self.mapfile, self.get_digest())

    def _extract_nb_players(self, s):
        try:
            self.nb_players_min = int(re.search("(?m)^nb_players_min[ \t]+([0-9]+)$", s).group(1))
        except:
            self.nb_players_min = 1
        try:
            self.nb_players_max = int(re.search("(?m)^nb_players_max[ \t]+([0-9]+)$", s).group(1))
        except:
            self.nb_players_max = 1

    def _load_header(self):
        try:
            s = self.read()
        except:
            s = ""
        self._extract_title(s)
        self._check_digest()
        self._extract_nb_players(s)

    def pack(self):
        if os.path.isfile(self.mapfile):
            map_name = os.path.split(self.mapfile)[-1]
            content = base64.b64encode(open(self.mapfile, "rb").read())
            return map_name + "***" + content
        else:
            dest = os.path.join(TMP_PATH, "map.tmp")
            z = zipdir.zipdir(self.mapfile, dest)
            content = base64.b64encode(open(dest, "rb").read())
            os.remove(dest)
            return "zip" + "***" + content

    def unpack(self, map_string):
        try:
            self.mapfile, content = map_string.split("***", 1)
            if self.mapfile != "zip":
                self.map_string = base64.b64decode(content)
                open(os.path.join(TMP_PATH, "recent_map.txt"), "wb").write(self.map_string)
            else:
                zf = os.path.join(TMP_PATH, "recent_map.tmp")
                open(zf, "wb").write(base64.b64decode(content))
                zd = os.path.join(TMP_PATH, "recent_map")
                shutil.rmtree(zd, True)
                zipdir.unzipdir(zf, zd)
                self.mapfile = zd
                os.remove(zf)
        except:
            exception("unpacking problem")

    def size(self):
        result = 0
        w = world.World([], 0)
        w.load_and_build_map(self)
        for sq in w.squares:
            result += len(sq.objects)
        for st in w.players_starts + w.computers_starts:
            result += len(st[1])
        return result

    _races = None
    
    @property
    def races(self):
        if self._races is None:
            w = world.World([], 0)
            w.load_and_build_map(self)
            self._races = w.get_races()
        return self._races
