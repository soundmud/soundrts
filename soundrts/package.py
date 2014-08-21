import os
import urllib

from constants import PACKAGES_METASERVER_URL
from lib.zipdir import unzipdir
from paths import MAPS_PATHS, PACKAGES_PATH, TMP_PATH


class Package(object):

    def __init__(self, url):
        self.name = url.split("/")[-1][:-4]
        self.url = url

    @property
    def is_active(self):
        return os.path.isdir(self.pathname)

    @property
    def pathname(self):
        return os.path.join(PACKAGES_PATH, self.name)

    @property
    def deactivated_pathname(self):
        return os.path.join(PACKAGES_PATH, "_" + self.name)

    def add(self, voice):
        if os.path.isdir(self.deactivated_pathname):
            os.rename(self.deactivated_pathname, self.pathname)
        self.update(voice)
    
    def deactivate(self):
        os.rename(self.pathname, self.deactivated_pathname)
    
    def update(self, voice):
        f = urllib.urlopen(self.url)
        remote_size = f.info()['Content-Length']
        try:
            local_size = open(os.path.join(PACKAGES_PATH, self.name + ".txt")).read()
        except:
            local_size = None
        if local_size != remote_size or \
                not os.path.isdir(self.pathname):
            voice.item([4328])
            zip_name = os.path.join(TMP_PATH, self.name + ".zip") 
            urllib.urlretrieve(self.url, zip_name)
            voice.item([4329])
            unzipdir(zip_name, PACKAGES_PATH, overwrite=True)
            open(os.path.join(PACKAGES_PATH, self.name + ".txt"), "w").write(remote_size)


_packages = None

def get_packages():
    global _packages
    if _packages is None:
        urls = urllib.urlopen(PACKAGES_METASERVER_URL).read().split("\n")
        _packages = [Package(u) for u in urls]
    return _packages

def get_all_packages_paths():
    return MAPS_PATHS + [p.pathname for p in get_packages() if p.is_active]