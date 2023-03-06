from hashlib import sha256
from pathlib import Path

import requests

from .lib.defs import preprocess
from .lib.log import warning
from .lib.voice import voice
from .lib.zipdir import zipdir, unzipdir
from .paths import DOWNLOADED_PACKAGES_PATH, CONFIG_DIR_PATH


# def update_packages_from_servers():
#     try:
#         r = requests.get("http://jlpo.free.fr/soundrts/package_servers.txt")
#         r.raise_for_status()
#     except requests.RequestException:
#         warning("couldn't download package servers list")
#     else:
#         for packages_url in r.iter_lines(decode_unicode=True):
#             _update_packages_from_server(packages_url)


def update_packages_from_servers():
    with open("cfg/package_servers.txt") as f:
        s = preprocess(f.read())
    for packages_url in s.split("\n"):
        packages_url = packages_url.strip()
        if packages_url:
            _update_packages_from_server(packages_url)


def _update_packages_from_server(server_url):
    try:
        r = requests.get(server_url + "index.txt")
        r.raise_for_status()
    except requests.RequestException:
        warning("couldn't download packages index from '%s'", server_url)
    else:
        for line in r.iter_lines(decode_unicode=True):
            try:
                name, digest = line.split()
            except ValueError:
                warning("wrong line in packages index: %s", line)
            else:
                _update_package(server_url, name, digest)


def _update_package(server_url, name, digest):
    package_path = Path(DOWNLOADED_PACKAGES_PATH).joinpath(name)
    if not package_path.exists() or sha256(package_path.read_bytes()).hexdigest() != digest:
        voice.alert(["updating", name])
        try:
            r = requests.get(server_url + name)
            r.raise_for_status()
        except requests.RequestException:
            warning("couldn't load package: %s", name)
            voice.alert(["error"])
        else:
            content_digest = sha256(r.content).hexdigest()
            if content_digest == digest:
                with open(package_path, "wb") as f:
                    f.write(r.content)
                voice.alert(["ok"])
            else:
                warning("wrong package digest for %s: %s", name, content_digest)
                voice.alert(["error"])


# The following functions are not called directly yet.
# They can be used to build a package server.

def build_packages_index():
    publish = Path(CONFIG_DIR_PATH, "editor", "export")
    files = []
    for path in publish.iterdir():
        if path.suffix == ".zip":
            name = path.name
            content = path.read_bytes()
            size = len(content)
            digest = sha256(content).hexdigest()
            files.append((size, name, digest))
    with open(publish.joinpath("index.txt"), "wt") as f:
        for _, name, digest in sorted(files):
            f.write(f"{name} {digest}\n")


def build_packages():
    edit = Path(CONFIG_DIR_PATH, "editor", "packages")
    publish = Path(CONFIG_DIR_PATH, "editor", "export")
    for path in edit.iterdir():
        name = path.name + ".package.zip"
        zipdir(str(path), publish.joinpath(name))
    build_packages_index()


def unpack_packages():
    edit = Path(CONFIG_DIR_PATH, "editor", "packages")
    reference = Path(CONFIG_DIR_PATH, "editor", "import")
    for path in reference.iterdir():
        if path.suffix == ".zip":
            destination = edit.joinpath(path.stem.replace(".package", ""))
            unzipdir(path, destination)
