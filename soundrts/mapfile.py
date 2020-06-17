import base64
try: 
    from hashlib import md5
except ImportError:
    from md5 import md5
import os.path
import re
import shutil

from .definitions import Style
from . import res
from .lib.log import debug, exception
from .lib import zipdir
from .paths import TMP_PATH
from . import world


class Map:

    map_string = None

    def __init__(self, p=None, digest="no_digest", official=False):
        self.path = p
        self.digest = digest
        self.official = official
        if p:
            self._load_header()

    def load_resources(self):
        from .clientmedia import sounds, res
        sounds.enter_map(res, self.path)

    def unload_resources(self):
        from .clientmedia import sounds
        sounds.exit_map()

    def load_rules_and_ai(self, res):
        from .definitions import rules, load_ai
        rules.load(res.get_text_file("rules", append=True), self.campaign_rules, self.additional_rules)
        load_ai(res.get_text_file("ai", append=True), self.campaign_ai, self.additional_ai)

    def load_style(self, res):
        from .definitions import style
        style.load(res.get_text_file("ui/style", append=True, localize=True), self.campaign_style, self.additional_style)

    def _read_additional_file(self, n):
        p = os.path.join(self.path, n)
        if os.path.isfile(p):
            return open(p).read()
        else:
            return ""

    def _read_campaign_file(self, n):
        if getattr(self, "campaign", None) is None:
            return ""
        p = os.path.join(self.campaign.path, n)
        if os.path.isfile(p):
            return open(p).read()
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
                       os.path.split(self.path)[-1])
        except:
            return "unknown"

    def read(self):
        if self.map_string is not None:
            return self.map_string
        elif os.path.isdir(self.path):
            return open(os.path.join(self.path, "map.txt")).read()
        else:
            return open(self.path).read()

    def _extract_title(self, s):
        m = re.search("(?m)^title[ \t]+([0-9 ]+)$", s)
        if m and not self.official:
            self.title = [int(x) for x in m.group(1).split(" ")]
        else:
            name = os.path.split(self.path)[1].lower()
            name = re.sub(r"\.txt$", "", name)
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
        return md5(s.encode()).hexdigest()

    def _check_digest(self):
        if self.digest is None:
            self.title.insert(0, 1097) # heal sound to alert player
        elif self.digest != "no_digest" and self.get_digest() != self.digest:
            self.title.insert(0, 1029) # hostile sound to alert player
            debug("%s\n>>>%s<<<", self.path, self.get_digest())

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

    _original_map_string = None

    def pack(self):
        if self._original_map_string is not None:
            return self._original_map_string.encode()
        if os.path.isfile(self.path):
            map_name = os.path.split(self.path)[-1]
            content = base64.b64encode(open(self.path, "rb").read())
            return map_name.encode() + b"***" + content
        else:
            dest = os.path.join(TMP_PATH, "map.tmp")
            z = zipdir.zipdir(self.path, dest)
            content = base64.b64encode(open(dest, "rb").read())
            os.remove(dest)
            return b"zip" + b"***" + content

    def unpack(self, map_string):
        self._original_map_string = map_string
        try:
            self.path, content = map_string.split("***", 1)
            if self.path != "zip":
                self.map_string = base64.b64decode(content).decode()
                open(os.path.join(TMP_PATH, "recent_map.txt"), "wb").write(self.map_string.encode())
            else:
                zf = os.path.join(TMP_PATH, "recent_map.tmp")
                open(zf, "wb").write(base64.b64decode(content).encode())
                zd = os.path.join(TMP_PATH, "recent_map")
                shutil.rmtree(zd, True)
                zipdir.unzipdir(zf, zd)
                self.path = zd
                os.remove(zf)
        except:
            exception("unpacking problem")
        else:
            self._load_header()

    def size(self):
        result = 0
        w = world.World([], 0)
        w.load_and_build_map(self)
        for sq in w.squares:
            result += len(sq.objects)
        for st in w.players_starts + w.computers_starts:
            result += len(st[1])
        return result

    _factions = None
    _mods = None
    
    @property
    def factions(self):
        if self._factions is None and self._mods != res.mods:
            w = world.World([], 0)
            w.load_and_build_map(self)
            self._factions = w.factions
            self._mods = res.mods
        return self._factions


def _add_official_multi(w):
    maps = [line.strip().split() for line in open("cfg/official_maps.txt")]
    for n, digest in maps:
        p = os.path.join("multi", n)
        w.append(Map(p, digest, official=True))

def _add_custom_multi(w):
    for pp in res.get_all_packages_paths():
        d = os.path.join(pp, "multi")
        if os.path.isdir(d):
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if os.path.normpath(p) not in (os.path.normpath(x.path) for x in w):
                    w.append(Map(p, None))

def _move_recommended_maps(w):
    style = Style()
    style.load(res.get_text_file("ui/style", append=True, localize=True))
    for n in reversed(style.get("parameters", "recommended_maps")):
        for m in reversed(w[:]): # reversed so the custom map is after the official map
            if m.get_name()[:-4] == n:
                w.remove(m)
                w.insert(0, m)

def _get_worlds_multi():
    w = []
    _add_official_multi(w)
    _add_custom_multi(w)
    _move_recommended_maps(w)
    return w

_multi_maps = None
_mods_at_the_previous_multi_maps_update = None

def worlds_multi():
    global _multi_maps, _mods_at_the_previous_multi_maps_update
    if _multi_maps is None or _mods_at_the_previous_multi_maps_update != res.mods:
        _multi_maps = _get_worlds_multi()
        _mods_at_the_previous_multi_maps_update = res.mods
    return _multi_maps
