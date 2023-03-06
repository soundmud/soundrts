import io
import os.path
import re
from hashlib import sha256
from zipfile import ZipFile

from .lib.package import ZipPackage, Package, resource_layer


def _name_from_path(path):
    name = os.path.basename(path)
    name = os.path.splitext(name)[0]
    name = re.sub("[^A-Za-z0-9._-]", "", name)
    return name


class Map:
    # stats, logs, replay menu... (not really an id though)
    name = "unknown"

    # raw content
    buffer: bytes
    buffer_name: str  # includes the extension for the filetype (check if zipfile?)

    # unpacked content
    definition: str = None
    resources = None

    # header (also in parsed definition)
    title: list
    nb_players_min: int
    nb_players_max: int

    def __init__(self, path: str = None):
        if path is not None:
            self._init_from_path(path)

    @staticmethod
    def load(f, name):
        m = Map()
        m._init_from_buffer(f.read(), name)
        return m

    def _load_from_text_file(self, f):
        self.definition = f.read()
        self._load_header()

    def _load_from_package(self, package):
        self.resources = resource_layer(package, self.name)
        self._load_from_text_file(self.resources.open_text("map.txt"))

    def _init_from_path(self, path):
        self.name = _name_from_path(path)
        if path.endswith(".txt"):
            f = open(path, encoding="utf-8", errors="replace")
            self._load_from_text_file(f)
        else:
            package = Package.from_path(path)
            self._load_from_package(package)

    @staticmethod
    def loads(buffer: bytes, name):
        map_ = Map()
        map_._init_from_buffer(buffer, name)
        return map_

    def _init_from_buffer(self, buffer, name_with_ext):
        self.buffer = buffer
        self.buffer_name = name_with_ext
        path = name_with_ext  # "short path" (Path.name)
        self.name = _name_from_path(path)
        if path.endswith(".txt"):
            s = buffer.decode(encoding="utf-8", errors="replace")
            f = io.StringIO(s, newline=None)
            self._load_from_text_file(f)
        else:
            package = ZipPackage(ZipFile(io.BytesIO(buffer)))
            self._load_from_package(package)

    def _load_header(self):
        self.title = self._extract_title()
        self.nb_players_min = self._find_int_from("nb_players_min", 1)
        self.nb_players_max = self._find_int_from("nb_players_max", 1)

    def _extract_title(self):
        return [f"{self.name}"] + self._title_from_definition()

    def _title_from_definition(self) -> list:
        line: str = self._find_a_line_with("title")
        if line:
            return [int(x) for x in line.split(" ")]
        else:
            return []

    def _find_a_line_with(self, keyword):
        match = re.search("(?m)^%s[ \t]+([0-9 ]+)$" % keyword, self.definition)
        if match:
            return match.group(1)

    def _find_int_from(self, keyword, default):
        line = self._find_a_line_with(keyword)
        if line:
            return int(line)
        else:
            return default

    def digest(self):
        return sha256(self.buffer).hexdigest()
