import io
import os
import zipfile
from pathlib import Path
from typing import IO
from zipfile import ZipFile

from soundrts.lib import encoding
from soundrts.lib.zipdir import zipdir


class Package:  # Dir? VirtualDir?
    """a (virtual) directory (actually in a filesystem or in a zip file)"""
    name = "default"

    @staticmethod
    def from_path(name: str):
        name = Path(name)
        if name.suffix in [".zip", ".pkg"]:
            return ZipPackage(ZipFile(name))
        else:
            return FolderPackage(name)

    def open_binary(self, name) -> IO: ...
    def dirnames(self): ...
    def filenames(self): ...
    def relative_paths_of_files_in_subtree(self, subdir): ...
    def subpackage(self, subdir): ...

    def open_text(self, name):
        b = self.open_binary(name)
        e = encoding.encoding(b.read(), name)
        b.seek(0)
        return io.TextIOWrapper(b, encoding=e, errors="replace")

    def isfile(self, name): ...
    def isdir(self, name): ...

    def is_a_soundpack(self):
        for name in ("rules.txt", "ai.txt"):
            if self.isfile(name):
                return False
        return True


class FolderPackage(str, Package):  # DirInFilesystem?

    def open_binary(self, name):
        path = os.path.join(self, name)
        # local folder reading by zipping the folder first
        if os.path.isdir(path):
            f = io.BytesIO()
            zipdir(path, f, compression=zipfile.ZIP_STORED)
            f.seek(0)
            return f
        return open(path, "rb")

    def isfile(self, name):
        path = os.path.join(self, name)
        return os.path.isfile(path)

    def isdir(self, name):
        path = os.path.join(self, name)
        return os.path.isdir(path)

    def dirnames(self):
        return next(os.walk(self))[1]

    def filenames(self):
        return next(os.walk(self))[2]

    def relative_paths_of_files_in_subtree(self, subdir):
        top = os.path.join(self, subdir)
        if os.path.isdir(top):
            for dirpath, _, filenames in os.walk(top):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    yield path[len(self)+1:]

    def subpackage(self, subdir):
        path = os.path.join(self, subdir)
        if os.path.isdir(path):
            return Package.from_path(path)


class ZipPackage(Package):  # DirInZip?
    def __init__(self, zipfile: ZipFile, subdir: str = None):
        self._zipfile = zipfile
        self._subdir = subdir

    def __repr__(self):
        if self._subdir is None:
            return f"<ZipPackage filename='{self._zipfile.filename}'>"
        else:
            return f"<ZipPackage filename='{self._zipfile.filename}' subdir='{self._subdir}'>"

    def dirnames(self):
        result = set()
        for name in self._namelist():
            try:
                name = Path(name).parts[0]
            except IndexError:
                pass
            else:
                if not self.isfile(name):
                    result.add(name)
        return result

    def filenames(self):
        result = set()
        for name in self._namelist():
            try:
                name = Path(name).parts[0]
            except IndexError:
                pass
            else:
                if self.isfile(name):
                    result.add(name)
        return result

    def relative_paths_of_files_in_subtree(self, path):
        for name in self._namelist():
            if name.startswith(path + "/"):
                yield name

    def subpackage(self, subdir):
        if subdir.endswith(".zip") and subdir in self._namelist():
            return ZipPackage(ZipFile(self.open_binary(subdir)))
        for name in self._namelist():
            if name.startswith(subdir + "/"):
                return ZipPackage(self._zipfile, self._path(subdir))

    def open_binary(self, name):
        return self._zipfile.open(self._path(name))

    def _path(self, name):
        if not self._subdir:
            return name
        else:
            return self._subdir + "/" + name

    def isfile(self, name):
        return self._path(name) in self._zipfile.namelist()

    def isdir(self, name):
        for n in self._namelist():
            if n.startswith(name + "/"):
                return True

    def _namelist(self):
        if self._subdir is None:
            return self._zipfile.namelist()
        else:
            return self._short_name_list()

    def _short_name_list(self):
        start = self._subdir + "/"
        for name in self._zipfile.namelist():
            if name.startswith(start):
                yield name[len(start):]


def resource_layer(package, name):
    if package:
        package.name = name
    return package


class PackageStack(list):
    def __init__(self, paths):
        list.__init__(self)
        self.extend(map(Package.from_path, paths))

    def mod(self, name):
        for package in reversed(self):
            subdir = "mods/" + name
            mod = resource_layer(package.subpackage(subdir), name)
            if mod:
                if mod.isfile("mod.txt"):
                    s = mod.open_text("mod.txt").read()
                    if s.startswith("mods "):
                        mod.mods = s.split(" ", 1)[1].split(",")
                return mod

    def mods(self):
        mod_names = set()
        for package in reversed(self):
            subdir = "mods"
            mods = package.subpackage(subdir)
            if mods is not None:
                mod_names.update(mods.dirnames())
        return [self.mod(name) for name in mod_names]
