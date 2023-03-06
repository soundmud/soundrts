import os

from soundrts import parameters


def _mkdir(path):
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except:
            # no log file at this stage
            print("cannot make dir: %s" % path)


if os.path.exists("user"):
    CONFIG_DIR_PATH = "user"
elif "APPDATA" in os.environ:  # Windows
    CONFIG_DIR_PATH = os.path.join(os.environ["APPDATA"], "SoundRTS")
elif "HOME" in os.environ:
    CONFIG_DIR_PATH = os.path.join(os.environ["HOME"], ".SoundRTS")
else:
    CONFIG_DIR_PATH = "user"
_mkdir(CONFIG_DIR_PATH)

TMP_PATH = os.path.join(CONFIG_DIR_PATH, "tmp")
_mkdir(TMP_PATH)

REPLAYS_PATH = os.path.join(CONFIG_DIR_PATH, "replays")
_mkdir(REPLAYS_PATH)

DOWNLOADED_PATH = os.path.join(CONFIG_DIR_PATH, "downloaded")
_mkdir(DOWNLOADED_PATH)

CLIENT_LOG_PATH = os.path.join(TMP_PATH, "client.log")
SERVER_LOG_PATH = os.path.join(TMP_PATH, "server.log")

CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "SoundRTS.ini")
CAMPAIGNS_CONFIG_PATH = os.path.join(CONFIG_DIR_PATH, "campaigns.ini")
STATS_PATH = os.path.join(CONFIG_DIR_PATH, "stats.tmp")
SAVE_PATH = os.path.join(CONFIG_DIR_PATH, "savegame")
CUSTOM_BINDINGS_PATH = os.path.join(CONFIG_DIR_PATH, "bindings.txt")

_mkdir(os.path.join(CONFIG_DIR_PATH, "single"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "multi"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "mods"))
_mkdir(os.path.join(CONFIG_DIR_PATH, "packages"))

_mkdir(os.path.join(DOWNLOADED_PATH, "multi"))
_mkdir(os.path.join(DOWNLOADED_PATH, "packages"))

DOWNLOADED_PACKAGES_PATH = os.path.join(DOWNLOADED_PATH, "packages")

BASE_PACKAGE_PATH = parameters.d["packages"]["base"]
BASE_PATHS = parameters.d["packages"]["additional"]


def packages_paths():
    packages = []
    packages.extend(BASE_PATHS)
    for rp in BASE_PATHS:
        pp = os.path.join(rp, "packages")
        if os.path.isdir(pp):
            for name in os.listdir(pp):
                p = os.path.join(pp, name)
                if os.path.normpath(p) != os.path.normpath(BASE_PACKAGE_PATH):
                    packages.append(p)
    return packages
