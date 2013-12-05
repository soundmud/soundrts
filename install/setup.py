from distutils.core import setup
import glob
import os
import os.path
import sys

import py2exe


PYGAME_DIR = os.path.join(os.path.split(sys.executable)[0],
                          "Lib\site-packages\pygame")

def data_files_from_tree(source_dir): # the installation directory must have the same name
    data_files = []
    for root, dirs, files in os.walk(source_dir):
        if ".svn" not in root:
            source_list = []
            for filename in files:
                source_list.append(os.path.join(root, filename))
            data_files.append((root, source_list))
    return data_files


setup(windows=["soundrts.py"],
      console=["server.py"],
      data_files=[("", [r"%s/freesansbold.ttf" % PYGAME_DIR]
##                   + glob.glob(r"%s/*.dll" % PYGAME_DIR)
                   ),
                  ],
      options = {'py2exe': {
      'bundle_files': 1,
      'excludes': ['tkinter', '_tkinter', 'Tkinter', 'numpy', ], 
      'dll_excludes': ['libiomp5md.dll',],
} },
##      zipfile = None,
      )
