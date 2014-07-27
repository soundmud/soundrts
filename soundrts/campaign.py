import ConfigParser
import re

from game import *
from msgs import nb2msg


class MissionChapter(Map):

    def __init__(self, p, campaign, id):
        Map.__init__(self, p)
        self.campaign = campaign
        self.id = id

    def _get_next(self):
        return self.campaign.get_next(self)

    def _victory(self):
        menu = clientmenu.Menu([], [])
        menu.append([4011], self._get_next()) # continue
        menu.append([4009], None) # cancel
        menu.run()
        
    def _defeat(self):
        menu = clientmenu.Menu([], [])
        menu.append([4266], self) # restart
        menu.append([4009], None) # cancel
        menu.run()

    def run(self):
        voice.important(self.title)
        game = MissionGame(self)
        game.run()
        self.run_next_step(game)

    def run_next_step(self, game):
        if game.has_victory():
            self.campaign.unlock_next(self)
            if self._get_next():
                self._victory()
        else:
            self._defeat()


class CutSceneChapter:

    def __init__(self, path, campaign=None, id=None):
        self.path = path
        self.campaign = campaign
        self.id = id
        self._load()

    def _load(self):
        s = open(self.path, "U").read() # "universal newlines"
        # header
        m = re.search("(?m)^title[ \t]+([0-9 ]+)$", s)
        if m:
            l = m.group(1).split(" ")
            l = [int(x) for x in l]
        else:
            l = nb2msg(self.id)
        self.title = l
        # content
        m = re.search("(?m)^sequence[ \t]+([0-9 ]+)$", s)
        if m:
            l = m.group(1).split(" ")
        else:
            l = []
        self.sequence = l

    def _get_next(self):
        return self.campaign.get_next(self)

    def run(self):
        voice.important(self.title)
        sounds.play_sequence(self.sequence)
        self.campaign.unlock_next(self)
        if self._get_next():
            self._get_next().run()


class Campaign(object):

    def __init__(self, path, title=None):
        self.path = path
        if title:
            self.title = title
        else:
            self.title = [os.path.split(path)[1]]
        self.chapters = []
        i = 0
        while True:
            cp = os.path.join(self.path, "%s.txt" % i)
            if not os.path.isfile(cp):
                cp = os.path.join(self.path, "%s" % i)
                if not os.path.isdir(cp):
                    break
            if os.path.isfile(cp) and \
               open(cp, "U").readline() == "cut_scene_chapter\n":
                c = CutSceneChapter(cp, campaign=self, id=i)
            else:
                c = MissionChapter(cp, campaign=self, id=i)
            self.chapters.append(c)
            i += 1

    def _get(self, id):
        if id < len(self.chapters):
            return self.chapters[id]
        else:
            return None

    def get_next(self, chapter):
        return self._get(chapter.id + 1)

    def _get_id(self):
        return re.sub("[^a-zA-Z0-9]", "_", self.path)

    def _get_bookmark(self):
        c = ConfigParser.SafeConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.readfp(open(CAMPAIGNS_CONFIG_PATH))
        try:
            return c.getint(self._get_id(), "chapter")
        except:
            return 0

    def _available_chapters(self):
        return self.chapters[:self._get_bookmark() + 1]

    def _set_bookmark(self, number):
        c = ConfigParser.SafeConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.readfp(open(CAMPAIGNS_CONFIG_PATH))
        if self._get_id() not in c.sections():
            c.add_section(self._get_id())
        c.set(self._get_id(), "chapter", repr(number))
        c.write(open(CAMPAIGNS_CONFIG_PATH, "w"))

    def unlock_next(self, chapter):
        if self._get_bookmark() == chapter.id:
            next_chapter = self.get_next(chapter)
            if next_chapter:
                self._set_bookmark(next_chapter.id)

    def run(self):
        sounds.enter_campaign(self.path)
        menu = clientmenu.Menu(self.title, [],
                default_choice_index=len(self._available_chapters()) - 1)
        for ch in self._available_chapters():
            menu.append(ch.title, ch)
#        menu.append([4113], "restore")
        menu.append([4118], None) # "cancel"
        menu.run()
        sounds.exit_campaign()
