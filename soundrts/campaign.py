import ConfigParser
import os
import re

from clientmedia import voice, sounds, play_sequence, res
from clientmenu import Menu
import config
from game import MissionGame
from mapfile import Map
from lib.msgs import nb2msg
from paths import CAMPAIGNS_CONFIG_PATH


class MissionChapter(Map):

    def __init__(self, p, campaign, id):
        Map.__init__(self, p)
        self.campaign = campaign
        self.id = id

    def _get_next(self):
        return self.campaign.get_next(self)

    def _victory(self):
        menu = Menu([], [])
        menu.append([4011], self._get_next()) # continue
        menu.append([4009], None) # cancel
        menu.run()
        
    def _defeat(self):
        menu = Menu([], [])
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
        play_sequence(self.sequence)
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
        p = os.path.join(self.path, "mods.txt")
        if os.path.isfile(p):
            self.mods = open(p).read()
        else:
            self.mods = None

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

    def load_resources(self):
        sounds.enter_campaign(res, self.path)

    def unload_resources(self):
        sounds.exit_campaign()

    def run(self):
        if self.mods is not None:
            res.set_mods(self.mods)
        try:
            self.load_resources()
            menu = Menu(self.title, [])
            if len(self._available_chapters()) > 1:
                ch = self._available_chapters()[-1]
                menu.append([4011] + ch.title, ch) # "continue"
            for ch in self._available_chapters():
                menu.append(ch.title, ch)
    #        menu.append([4113], "restore")
            menu.append([4118], None) # "cancel"
            menu.run()
        finally:
            self.unload_resources()
