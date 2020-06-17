import threading
import urllib.request, urllib.parse, urllib.error

from .clientmedia import voice
from .metaserver import METASERVER_URL
from . import msgparts as mp
from .paths import STATS_PATH, OLD_STATS_PATH
from . import stats
from .version import VERSION, IS_DEV_VERSION


class RevisionChecker(threading.Thread):

    daemon = True
    never_started = True

    def run(self):
        if IS_DEV_VERSION:
            return
        try:
            stage = ".".join(VERSION.split(".")[:2])
            url = "http://jlpo.free.fr/soundrts/%sversion.txt" % stage
            rev = urllib.request.urlopen(url).read().strip()
            if (rev != VERSION) and (rev.find("404") == -1):
                voice.important(mp.UPDATE_AVAILABLE)
            stats.Stats(OLD_STATS_PATH, METASERVER_URL).send()
            stats.Stats(STATS_PATH, METASERVER_URL).send()
        except:
            pass

    def start_if_needed(self):
        if self.never_started:
            self.start()
            self.never_started = False


revision_checker = RevisionChecker()
