import os
import os.path


def _my_mkdir(path):
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except:
            # no log file at this stage
            print "cannot make dir: %s" % path

def _get_stage():
    stage = open("cfg/stage.txt").read().strip()
    if stage == "stable":
        return ""
    else:
        return " " + stage

if os.path.exists("user"):
    CONFIG_DIR_PATH = "user"
elif os.environ.has_key("APPDATA"): # Windows XP
    CONFIG_DIR_PATH = os.path.join(os.environ["APPDATA"], "SoundRTS%s" % _get_stage())
elif os.environ.has_key("HOME"): # Linux
    CONFIG_DIR_PATH = os.path.join(os.environ["HOME"], ".SoundRTS%s" % _get_stage())
else: # Windows 95, Windows 98 ?
    CONFIG_DIR_PATH = os.getcwd()
if not os.path.exists(CONFIG_DIR_PATH):
    os.mkdir(CONFIG_DIR_PATH)

TMP_PATH = os.path.join(CONFIG_DIR_PATH, "tmp")
if not os.path.exists(TMP_PATH):
    os.mkdir(TMP_PATH)

CLIENT_LOG_PATH = os.path.join(TMP_PATH, "client.log")
SERVER_LOG_PATH = os.path.join(TMP_PATH, "server.log")
MAPERROR_PATH = os.path.join(TMP_PATH, "maperror.txt")

CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "SoundRTS.ini")
CAMPAIGNS_CONFIG_PATH = os.path.join(CONFIG_DIR_PATH, "campaigns.ini")
OLD_STATS_PATH = os.path.join(CONFIG_DIR_PATH, "stats.txt")
STATS_PATH = os.path.join(CONFIG_DIR_PATH, "stats.tmp")
SAVE_PATH = os.path.join(CONFIG_DIR_PATH, "savegame")

MAPS_PATHS = ["", CONFIG_DIR_PATH]
if MAPS_PATHS[0] == MAPS_PATHS[1]:
    del MAPS_PATHS[1]
else:
    _my_mkdir(os.path.join(CONFIG_DIR_PATH, "single"))
    _my_mkdir(os.path.join(CONFIG_DIR_PATH, "multi"))
    _my_mkdir(os.path.join(CONFIG_DIR_PATH, "mods"))
