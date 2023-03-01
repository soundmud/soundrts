from cx_Freeze import setup, Executable

from soundrts.version import VERSION

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {'packages': [], 'excludes': []}

import sys
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('soundrts.py', base=base)
]

setup(name='soundrts',
      version = VERSION.replace("-dev", ".9999"),
      description = '',
      options = {'build_exe': build_options},
      executables = executables)
