"""Packages that can be installed, uninstalled, and updated through the network.
Only the resource loader decides how packages act over the resource tree."""

import os
import urllib.request, urllib.parse, urllib.error

from .log import warning
import zipfile


class PackageManager:
    """The package manager."""
    def __init__(self, packages_metaserver_url, tmp_path, packages_path, say_downloading, say_extracting):
        """
        tmp_path -- This is where the downloaded archives will be stored.
        packages_path -- This is where the packages will be installed.
        """
        self.packages_metaserver_url = packages_metaserver_url
        self.tmp_path = tmp_path
        self.packages_path = packages_path
        self.say_downloading = say_downloading
        self.say_extracting = say_extracting
        self.packages_urls_cache_path = os.path.join(self.tmp_path, "packages_urls.txt")
        self.packages = [DownloadablePackage(u, self) for u in self.get_packages_urls()]

    def get_packages_urls(self):
        try:
            urls = urllib.request.urlopen(self.packages_metaserver_url).read()
            open(self.packages_urls_cache_path, "w").write(urls)
        except OSError:
            try:
                urls = open(self.packages_urls_cache_path).read()
            except OSError:
                urls = ""
        urls += "\n" + open("cfg/additional_packages_urls.txt").read()
        return [url.strip() for url in urls.split("\n") if url.strip()]

    def get_packages_paths(self):
        return [p.pathname for p in self.installed_packages]

    @property
    def uninstalled_packages(self):
        return [p for p in self.packages if not p.is_active]

    @property
    def installed_packages(self):
        return [p for p in self.packages if p.is_active]


class DownloadablePackage:
    """a downloadable package

    (its name is guessed from its URL)
    """
    author = None
    index = None
    description = None
    def __init__(self, url, manager):
        self.name = url.split("/")[-1][:-4]
        self.url = url
        self.manager = manager

    @property
    def tmp_path(self):
        return self.manager.tmp_path

    @property
    def packages_path(self):
        return self.manager.packages_path

    @property
    def is_active(self):
        return os.path.isdir(self.pathname)

    @property
    def pathname(self):
        return os.path.join(self.packages_path, self.name)

    @property
    def deactivated_pathname(self):
        return os.path.join(self.packages_path, "_" + self.name)

    def install(self):
        """Install the package to the packages cache."""
        if os.path.isdir(self.deactivated_pathname):
            os.rename(self.deactivated_pathname, self.pathname)
        self.update()

    def uninstall(self):
        """Uninstall the package from the packages cache."""
        os.rename(self.pathname, self.deactivated_pathname)

    def _unzip(self, zip_name):
        z = zipfile.ZipFile(zip_name)
        for name in z.namelist():
            if name.startswith(self.name) and ".." not in name:
                z.extract(name, self.packages_path)
            else:
                warning("didn't extract %s", name)

    def size_filename(self):
        return os.path.join(self.packages_path, self.name + ".txt")

    def update(self):
        """Update the package from the network."""
        f = urllib.request.urlopen(self.url)
        remote_size = f.info()['Content-Length']
        try:
            local_size = open(self.size_filename()).read()
        except:
            local_size = None
        if local_size != remote_size or \
                not os.path.isdir(self.pathname):
            self.manager.say_downloading()
            zip_name = os.path.join(self.tmp_path, self.name + ".zip")
            urllib.request.urlretrieve(self.url, zip_name)
            self.manager.say_extracting()
            self._unzip(zip_name)
            open(self.size_filename(), "w").write(remote_size)
