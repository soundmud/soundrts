import threading
import urllib

from clientmedia import *
from commun import *
import config
from constants import *
import stats


class RevisionChecker(threading.Thread):

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
            stats.Stats(config.OLD_STATS_PATH, METASERVER_URL).send()
            stats.Stats(config.STATS_PATH, METASERVER_URL).send()
        except:
            pass

    def start_if_needed(self):
        if self.never_started:
            self.start()
            self.never_started = False


revision_checker = RevisionChecker()
