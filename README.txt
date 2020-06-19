SoundRTS is a real-time strategy audio game.

Feel free to experiment on the code base, but don't feel obliged to contribute back.

The license for the Python source code is a BSD 3-clause license (LICENSE.txt).
The license for the rest is unclear at the moment.

Tested with Python 3.8.

To install the requirements:
pip install -r requirements.txt -U

Running server.py doesn't require any package.

Running soundrts.py requires:
* pygame
* accessible_output2

Building a package requires also:
* docutils
* cx_Freeze

Testing requires:
* pytest

Official SoundRTS web site: http://jlpo.free.fr/soundrts