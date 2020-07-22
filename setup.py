#! python3
"""
From the command-line: py setup.py build
"""

import os
import shutil
from subprocess import Popen, check_output

from cx_Freeze import setup, Executable

import builddoc
import buildmultimapslist
from soundrts.version import VERSION


try:
    full_version = check_output(["git", "describe", "--tags"]).strip().decode()
except FileNotFoundError:
    print("WARNING: couldn't get version from git.")
    full_version = f"{VERSION}-unknown"
TMP = os.environ["TMP"]
destination = rf"{TMP}\soundrts-{VERSION}-windows"
build_exe_options = {
    'build_exe': destination,
    'optimize': 1,
    'silent': True,
    'packages': [],
    'excludes': ["Cython", "scipy", "numpy", "tkinter"],
    'include_files': ["res", "single", "multi", "mods", "cfg", "doc"],
    'replace_paths': [("*", f"{full_version}:")],
}
executables = [
    Executable('soundrts.py', base="Win32GUI"),
    Executable('server.py', base=None)
]

buildmultimapslist.build()
builddoc.build()
if os.path.exists(destination):
    print(f"{destination} already exists. Deleting...")
    shutil.rmtree(destination)
setup(options={'build_exe': build_exe_options},
      executables=executables,
      name="SoundRTS",
      version=VERSION.replace("-dev", ".9999"))
print("Creating empty user folder...")
os.mkdir(rf"{destination}\user")
print(r"Resetting cfg\language.txt ...")
open(rf"{destination}\cfg\language.txt", "w").write("")
Popen(rf'explorer /select,"{destination}"')
print("Adding full_version.txt ...")
with open(rf"{destination}\lib\full_version.txt", "w") as t:
    t.write(full_version)
