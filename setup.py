#! python3
"""
From the command-line: py setup.py build
"""

import os
import shutil
from subprocess import Popen

from cx_Freeze import setup, Executable

import builddoc
import buildmultimapslist
from soundrts.version import VERSION

TMP = os.environ["TMP"]
destination = rf"{TMP}\soundrts-{VERSION}-windows"
build_exe_options = {
    'build_exe': destination,
    'optimize': 1,
    'silent': True,
    'packages': [],
    'excludes': ["Cython", "scipy", "numpy", "tkinter"],
    'include_files': ["res", "single", "multi", "mods", "cfg", "doc"],
    'replace_paths': [("*", "")],
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
