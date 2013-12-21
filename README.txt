SoundRTS is a real-time strategy audio game.

Warning: the source code is the contorted result of a lot of iterations on an ever-evolving prototype. Some refactorings made things even worse. Sorry for that.

The license for the Python source code is a BSD 3-clause license (LICENSE.txt).
The license for the rest is unclear at the moment.

Running the game from the source (soundrts.py for the client, server.py for the standalone server) might require:
* Python 2.4 or later (Python 2.5 used to be the recommended version, but Python 2.7 might be a better choice now)
* Pygame 1.7.1 or later (Pygame 1.7.1 used to be the recommended version, but a later Pygame might work)
* win32com (if you use SAPI 5)

Building the binaries (with build-all.bat) might require:
* py2exe (Windows binary)

Official SoundRTS web site: http://jlpo.free.fr/soundrts