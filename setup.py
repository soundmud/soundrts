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
dest = rf"{TMP}\soundrts-{VERSION}-windows"
build_options = {'build_exe': dest,
                 'optimize': 1,
                 'silent': True,
                 'packages': [],
                 'excludes': ["Cython", "scipy", "numpy", "tkinter"],
                 'include_files': ["res", "single", "multi", "mods", "cfg", "doc"]}
executables = [
    Executable('soundrts.py', base="Win32GUI"),
    Executable('server.py', base=None)
]


buildmultimapslist.build()
builddoc.build()
if os.path.exists(dest):
    print(f"{dest} already exists. Deleting...")
    shutil.rmtree(dest)
setup(options = {'build_exe': build_options},
      executables = executables,
      name = "SoundRTS",
      version = VERSION.replace("-dev", ".9999"))
print("Creating empty user folder...")
os.mkdir(rf"{dest}\user")
print(r"Reseting cfg\language.txt ...") 
open(rf"{dest}\cfg\language.txt", "w").write("")
Popen(rf'explorer /select,"{dest}"')
