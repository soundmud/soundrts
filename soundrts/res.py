import locale
import os

import config
from lib.log import warning
from package import get_all_packages_paths


def _localize(p, lang):
    a, b = os.path.split(p)
    if b == "ui":
        return os.path.join(a, b + "-" + lang)
    else:
        a1, a2 = os.path.split(a)
        if a2 == "ui":
            return os.path.join(a1, a2 + "-" + lang, b)
        else:
            return p

##assert _localize("/ui", "fr").replace("\\", "/") == "/ui-fr"
##assert _localize("/ui/", "fr").replace("\\", "/") == "/ui-fr/"
##assert _localize("/uii", "fr").replace("\\", "/") == "/uii"
##assert _localize("/oui", "fr").replace("\\", "/") == "/oui"
##assert _localize("/ui/i", "fr").replace("\\", "/") == "/ui-fr/i"
##assert _localize("/ui/io/i", "fr").replace("\\", "/") == "/ui/io/i"
##assert _localize("/oui/i", "fr").replace("\\", "/") == "/oui/i"

def _available_languages():
    result = ["en"]
    for n in os.listdir(_r.mods[0]):
        if n.startswith("ui-"):
            result.append(n[3:])
    return result

def _best_language_match(lang):
    if lang is None:
        lang = ""
    a = _available_languages()
    # full match
    lang = lang.replace("_", "-")
    for c in a:
        if lang.lower() == c.lower():
            return c
    # ignore the second part
    if "-" in lang:
        lang = lang.split("-")[0]
    # match a short code
    for c in a:
        if lang.lower() == c.lower():
            return c
    # match a long code
    for c in a:
        if "-" in c:
            c0 = c.split("-")[0]
            if lang.lower() == c0.lower():
                return c
    # default value
    return "en"

def _get_language():
    cfg = open("cfg/language.txt").read().strip()
    if cfg:
        lang = cfg
    else:
        try:
            lang = locale.getdefaultlocale()[0]
        except ValueError:
            lang = "en"
            warning("Couldn't get the system language. "
                    "To use another language, edit 'cfg/language.txt' "
                    "and write 'pl' for example.")
    return _best_language_match(lang)
    

class ResourceLoader(object):

    def __init__(self):
        self.mods = []
        self.language = ""
        self.alerts = []
        self.update_mods_list()

    def update_mods_list(self):
        self.mods = []
        self.mods.append("res") # "vanilla mod"
        for p in config.mods.split(","):
            p = p.strip()
            if p:
                mod_found = False
                # get_all_packages_paths() is reversed so the latest path
                # takes precedence over the previous ones.  
                for root in reversed(get_all_packages_paths()):
                    path = os.path.join(root, "mods", p)
                    if os.path.exists(path):
                        self.mods.append(path)
                        mod_found = True
                        break
                if not mod_found:
                    mods = config.mods.split(",")
                    mods.remove(p)
                    config.mods = ",".join(mods)
                    self.alerts.append([1029, 4330, p])

    def exists(self, name):
        pass

    def _paths(self, p, locale):
        result = [p]
        if locale and self.language:
            result.append(_localize(p, self.language))
        return result

    def get_texts(self, name, locale=False, root=None):
        name += ".txt"
        if root is None:
            roots = self.mods
        else:
            roots = [root]
        result = []
        for pk in roots:
            for p in self._paths(os.path.join(pk, name), locale):
                if os.path.isfile(p):
                    result.append(open(p, "rU").read())
        return result
        
    def get_text(self, name, locale=False, append=False, root=None):
        if append:
            return "\n".join(self.get_texts(name, locale, root))
        else:
            return self.get_texts(name, locale, root)[-1]

    def get_sound_paths(self, path, root=None):
        if root is None:
            roots = self.mods
        else:
            roots = [root]
        result = []
        for pk in roots:
            result.extend(self._paths(os.path.join(pk, path), True))
        return reversed(result)


_r = ResourceLoader()
_r.language = _get_language()
get_text = _r.get_text
get_texts = _r.get_texts
get_sound_paths = _r.get_sound_paths
update_mods_list = _r.update_mods_list
alerts = _r.alerts

##assert _best_language_match("en") == "en"
##assert _best_language_match("fr_ca") == "fr"
##assert _best_language_match("fr") == "fr"
##assert _best_language_match("pt_BR") == "pt-BR"
##assert _best_language_match("pt_br") == "pt-BR"
##assert _best_language_match("pt") == "pt-BR"
##assert _best_language_match("de") == "de"
##assert _best_language_match("pl") == "pl"
##assert _best_language_match("es") == "es"
