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
    my_mkdir(dest)
    for n in listdir(src):
        if n[-len(ext):] == ext:
            copy(join(src, n), dest)

def my_copytree(src, dest, no_duplicate=False):
    if exists(dest):
        rmtree(dest)
    _copytree(src, dest, no_duplicate=no_duplicate)

def _copytree(src, dst, symlinks=False, no_duplicate=False):
    names = os.listdir(src)
    my_mkdir(dst)
    errors = []
    for name in names:
        if name == ".svn":
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                _copytree(srcname, dstname, symlinks, no_duplicate)
            elif not no_duplicate or not_a_duplicate(dstname):
                copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, why))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error, err:
            errors.extend(err.args[0])
    if errors:
        raise Error, errors

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

my_copy("soundrts", ".py", _d("bin/soundrts"))
my_copy("soundrts/lib", ".py", _d("bin/soundrts/lib"))
copy("install/setup.py", _d("bin"))
copy("soundrts.py", _d("bin"))
copy("server.py", _d("bin"))
chdir(_d("bin"))
cmd = "%s setup.py -q py2exe" % sys.executable
# cmd = "%s -OO setup.py -q py2exe" % sys.executable # and add "optimize: 2" to setup.py
print "py2exe... (%s)" % cmd
my_execute(cmd)
os.remove("setup.py")

print "multiplatform version"
my_copy("", "soundrts.py", "multi")
my_copy("", "server.py", "multi")
my_copytree("soundrts", "multi/soundrts")
chdir("multi")
for pythonver in (4, 6, 7, 5):
    print "compiling all using 2.%s..." % pythonver
    # force compilation
    for base in ("soundrts", "soundrts/lib"):
        for nf in os.listdir(base):
            if nf[-4:] == ".pyc":
                os.remove(os.path.join(base, nf))
            
    my_execute("c:\\python2%s\\python.exe -m compileall -ql soundrts soundrts/lib" % pythonver)
    my_copy("soundrts", ".pyc", "soundrts_python2%s" % pythonver)
    my_copy("soundrts/lib", ".pyc", "soundrts_python2%s/lib" % pythonver)
for base in ("soundrts", "soundrts/lib"):
    for nf in os.listdir(base):
        if nf[-3:] == ".py": # and nf not in ("soundrts.py", "server.py"):
            os.remove(os.path.join(base, nf))
print "2.%s is kept as a default for the multiplatform version." % pythonver

chdir(SRC_DIR)

copy("doc/readme.txt", _d("bin/multi"))
print "copying build_tts lib..."
my_copy("", ".dll", _d("bin/dist"))

for n in ("version.txt", "version-name.txt", "cfg/stage.txt",
          "stage-name.txt"):
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

        my_copy("doc/en", ".htm", dest + "doc") # English doc by default

        for e in [".php", ".txt"]:
            my_copy("metaserver", e, dest + "metaserver")
except:
    exception("error")
    raw_input("[press ENTER to exit]")
