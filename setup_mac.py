from cx_Freeze import setup, Executable

from soundrts.version import VERSION

import sys
import os

build_options = {
    "packages": ["pygame", "accessible_output2", "chardet", "cloudpickle", "requests"],
    "excludes": ["Cython", "scipy", "numpy", "tkinter"],
    "include_files": ["res", "single", "mods", "cfg"],
}

executables = [
    Executable("soundrts.py", base=None, target_name="soundrts")
]

setup(
    name="SoundRTS",
    version=VERSION.replace("-dev", ".9999"),
    description="SoundRTS audio game",
    options={"build_exe": build_options},
    executables=executables,
)
