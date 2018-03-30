#! python2.7
import compileall
from logging import *
import os
from os import mkdir, chdir, listdir, popen, popen2, popen3
from os.path import exists, join
import re
from shutil import *
import sys


SRC_DIR = os.getcwd()
TMP_DIR = os.environ["TMP"]
VERSION_TXT = open("version.txt").read().strip()
VERSION = re.search('VERSION = "([^"]+)"', open("soundrts/version.py").read()).group(1)
if VERSION != VERSION_TXT:
    print "different versions: %s (version.txt) and %s (Python files)" % (VERSION_TXT, VERSION)
    raw_input("[press ENTER to exit]")
    sys.exit()
else:
    print VERSION

def not_a_duplicate(dstname):
    return not (dstname.endswith(".ogg") and
           exists(re.sub(r"[/\\]res[/\\]ui[/\\]", "/res/ui-%s/" % p, dstname)))

def _d(path):
    return os.path.join(TMP_DIR, "soundrts/build", path)

def my_mkdir(path):
    if not exists(path):
        os.makedirs(path)

def my_copy(src, ext, dest):
    if src == "": src = "."
    my_mkdir(dest)
    for n in listdir(src):
        if n.endswith(ext):
            copy(join(src, n), dest)

def my_copytree(src, dest, *args, **kwargs):
    if exists(dest):
        rmtree(dest)
    copytree(src, dest, *args, **kwargs)

def my_execute(cmd):
    stdin, stdout, stderr = popen3(cmd)
    while True:
        s = stdout.readline()
        if s:
            print s.rstrip()
        else:
            break
    while True:
        s = stderr.readline()
        if s:
            print s.rstrip()
        else:
            break

print "updating list of maps..."
import buildmultimapslist
assert open("cfg/official_maps.txt").read()

my_copytree("soundrts", _d("bin/soundrts"),
            ignore=ignore_patterns("tests", "*.pyc"))
copy("install/setup.py", _d("bin"))
copy("soundrts.py", _d("bin"))
copy("server.py", _d("bin"))
chdir(_d("bin"))
cmd = "c:\\python27\\python.exe setup.py -q py2exe"
# cmd = "c:\\python27\\python.exe -OO setup.py -q py2exe" # and add "optimize: 2" to setup.py
print "py2exe... (%s)" % cmd
my_execute(cmd)
os.remove("setup.py")

print "multiplatform version"
my_copy("", "soundrts.py", "multi")
my_copy("", "server.py", "multi")
my_copytree("soundrts", "multi/soundrts")
chdir("multi")
pythonver = 7
print "compiling all using 2.%s..." % pythonver
my_execute("c:\\python2%s\\python.exe -m compileall -q soundrts" % pythonver)
# remove the *.py source files
for dirpath, dirnames, filenames in os.walk("soundrts"):
    for name in filenames:
        if name.endswith(".py"):
            os.remove(os.path.join(dirpath, name))

chdir(SRC_DIR)

copy("doc/multiplatform/readme.txt", _d("bin/multi"))
print "copying build_tts lib..."
my_copy("", ".dll", _d("bin/dist"))

for n in ("version.txt", "version-name.txt", "cfg/stage.txt",
          "stage-name.txt",
          "install/soundrts.iss", "install/ChineseSimp-12-5.1.11.isl"):
    copy(n, _d(""))

try:
    print "copying Windows version..."
    my_copytree(_d("bin/dist"), _d("soundrts-%s-windows/" % (VERSION,)))

    print "copying multiplatform version..."
    multi = _d("soundrts-%s/" % (VERSION,))
    my_copytree(_d("bin/multi"), multi)

    print "copying data files..."
    for dest in (_d("soundrts-%s-windows/" % (VERSION,)), multi):
        print dest
        my_mkdir(dest + "user")
        my_copytree("res", dest + "res")
        my_copytree("single", dest + "single")
        my_copytree("multi", dest + "multi")
        my_copy("res", ".txt", dest + "res")
        my_copytree("mods", dest + "mods")
        my_copytree("cfg", dest + "cfg")
        open(dest + "cfg/language.txt", "w").write("")
        my_copytree("mods", dest + "mods")

        my_copytree(_d("doc"), dest + "doc")

        for e in [".php", ".txt"]:
            my_copy("metaserver", e, dest + "metaserver")
except:
    exception("error")
    raw_input("[press ENTER to exit]")
