import threading
import urllib

from clientmedia import voice
from constants import METASERVER_URL
from paths import STATS_PATH, OLD_STATS_PATH
import stats
from version import VERSION


class RevisionChecker(threading.Thread):

    daemon = True
    never_started = True

    def run(self):
        if VERSION[-4:] == "-dev":
            return
        try:
            stage = file("stage.txt").read().strip()
            url = "http://jlpo.free.fr/soundrts/%sversion.txt" % stage
            rev = urllib.urlopen(url).read().strip()
            if (rev != VERSION) and (rev.find("404") == -1):
                voice.important([4234])
            stats.Stats(OLD_STATS_PATH, METASERVER_URL).send()
            stats.Stats(STATS_PATH, METASERVER_URL).send()
        except:
            pass

    def start_if_needed(self):
        if self.never_started:
            self.start()
            self.never_started = False


revision_checker = RevisionChecker()
