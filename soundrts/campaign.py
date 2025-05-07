import configparser
import os
import re
from pathlib import Path

from . import msgparts as mp
from .clientmedia import play_sequence, voice
from .clientmenu import Menu
from .game import MissionGame
from .lib.package import resource_layer
from .lib.msgs import nb2msg
from .lib.resource import res
from .mapfile import Map
from .paths import CAMPAIGNS_CONFIG_PATH


class Chapter:
    campaign: "Campaign"
    number: int

    def _next(self):
        return self.campaign.next(self)


class MissionChapter(Chapter):
    def __init__(self, campaign, number, map_):
        self.campaign = campaign
        self.number = number
        self.map = map_

    @property
    def title(self):
        return self.map.title[1:]

    def _run_victory_menu(self):
        menu = Menu()
        menu.append(mp.CONTINUE, self._next())
        menu.append(mp.QUIT, None)
        menu.run()

    def _run_defeat_menu(self):
        menu = Menu()
        menu.append(mp.RESTART, self)
        menu.append(mp.QUIT, None)
        menu.run()

    def run(self):
        voice.important(self.title)
        game = MissionGame(self)
        game.run()
        self.run_next_step(game)

    def run_next_step(self, game):
        if game.has_victory():
            self.campaign.unlock_next(self)
            if self._next():
                self._run_victory_menu()
        else:
            self._run_defeat_menu()


class CutSceneChapter(Chapter):
    def __init__(self, campaign, number, path):
        self.path = path
        self.campaign = campaign
        self.number = number
        self._load()

    def _load(self):
        s = self.campaign.resources.open_text(self.path).read()
        # header
        m = re.search("(?m)^title[ \t]+([0-9 ]+)$", s)
        if m:
            title = m.group(1).split(" ")
            title = [int(x) for x in title]
        else:
            title = nb2msg(self.number)
        self.title = title
        # content
        m = re.search("(?m)^sequence[ \t]+([0-9 ]+)$", s)
        if m:
            sequence = m.group(1).split(" ")
        else:
            sequence = []
        self.sequence = sequence

    def run(self):
        voice.important(self.title)
        play_sequence(self.sequence)
        self.campaign.unlock_next(self)
        if self._next():
            self._next().run()


class Campaign:
    def _id(self):
        return re.sub("[^a-zA-Z0-9]", "_", self.name)

    def __init__(self, package, path):
        self.name = Path(path).stem
        self.resources = resource_layer(package, self.name)
        self._set_title_and_mods()
        self._set_mods_from_mods_txt()
        self._set_chapters()

    def _set_title_and_mods(self):
        if self.resources.isfile("campaign.txt"):
            s = self.resources.open_text("campaign.txt").read()
        else:
            s = ""
        m = re.search("(?m)^title[ \t]+([A-Za-z0-9 ]+)$", s)
        if m:
            self.title = m.group(1).split(" ")
        else:
            self.title = [self.name]
        m = re.search("(?m)^mods[ \t]+([A-Za-z0-9 ]+)$", s)
        if m:
            self.mods = m.group(1)
        elif re.search("(?m)^mods$", s):
            self.mods = ""
        else:
            self.mods = None

    def _set_mods_from_mods_txt(self):
        if self.resources.isfile("mods.txt"):
            self.mods = self.resources.open_text("mods.txt").read()

    def _set_chapters(self):
        self.chapters = []
        number = 0
        while True:
            filename = f"{number}.txt"
            if not self.resources.isfile(filename):
                filename = f"{number}.zip"
                if not self.resources.isfile(filename):
                    break
            if self._is_a_cutscene(filename):
                c = CutSceneChapter(self, number, filename)
            else:
                file = self.resources.open_binary(filename)
                map_ = Map.load(file, filename)
                map_.name = self.name + "/" + str(number)
                c = MissionChapter(self, number, map_)
            self.chapters.append(c)
            number += 1

    def _is_a_cutscene(self, path):
        if path.endswith(".txt"):
            with self.resources.open_text(path) as t:
                return t.readline() == "cut_scene_chapter\n"

    def chapter(self, number):
        if number < len(self.chapters):
            return self.chapters[number]
        else:
            return None

    def next(self, chapter):
        return self.chapter(chapter.number + 1)

    def _get_bookmark(self):
        c = configparser.ConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.read_file(open(CAMPAIGNS_CONFIG_PATH))
        return c.getint(self._id(), "chapter", fallback=0)

    def _available_chapters(self):
        return self.chapters[: self._get_bookmark() + 1]

    def _set_bookmark(self, number):
        c = configparser.ConfigParser()
        if os.path.isfile(CAMPAIGNS_CONFIG_PATH):
            c.read_file(open(CAMPAIGNS_CONFIG_PATH))
        if self._id() not in c.sections():
            c.add_section(self._id())
        c.set(self._id(), "chapter", repr(number))
        c.write(open(CAMPAIGNS_CONFIG_PATH, "w"))

    def unlock_next(self, chapter):
        if self._get_bookmark() == chapter.number:
            next_chapter = self.next(chapter)
            if next_chapter:
                self._set_bookmark(next_chapter.number)

    def run(self):
        if self.mods is not None:
            res.set_mods(self.mods)
        try:
            res.set_campaign(self)
            self.menu().run()
        finally:
            res.set_campaign()

    def menu(self):
        menu = Menu(self.title)
        if len(self._available_chapters()) > 1:
            chapter = self._available_chapters()[-1]
            menu.append(mp.CONTINUE + chapter.title, chapter)
        for chapter in self._available_chapters():
            prefix = nb2msg(chapter.number) if chapter.number > 0 else []
            menu.append(prefix + chapter.title, chapter)
        menu.append(mp.BACK, None)
        return menu
