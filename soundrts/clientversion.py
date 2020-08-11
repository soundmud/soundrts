import threading
import urllib.error
import urllib.parse
import urllib.request

from . import msgparts as mp
from . import stats
from .clientmedia import voice
from .metaserver import METASERVER_URL
from .paths import OLD_STATS_PATH, STATS_PATH
from .version import VERSION


def _patch(version):
    try:
        return int(version.split(".")[2])
    except (ValueError, IndexError):
        return -1


class RevisionChecker(threading.Thread):

    daemon = True
    never_started = True

    def run(self):
        try:
            if _patch(VERSION) != -1:
                major_minor = ".".join(VERSION.split(".")[:2])
                url = f"http://jlpo.free.fr/soundrts/{major_minor}version.txt"
                latest_version = urllib.request.urlopen(url).read().strip().decode()
                if "404" not in latest_version and _patch(VERSION) < _patch(latest_version):
                    voice.important(mp.UPDATE_AVAILABLE)
        except:
            pass
        try:
            stats.Stats(OLD_STATS_PATH, METASERVER_URL).send()
            stats.Stats(STATS_PATH, METASERVER_URL).send()
        except:
            pass

    def start_if_needed(self):
        if self.never_started:
            self.start()
            self.never_started = False


revision_checker = RevisionChecker()
