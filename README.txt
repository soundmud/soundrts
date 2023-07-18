SoundRTS is a real-time strategy audio game.

Feel free to experiment on the code base, but don't feel obliged to contribute back.

The license for the Python source code is a BSD 3-clause license (LICENSE.txt).
The license for the rest is unclear at the moment.

Tested with Python 3.8.

To install the requirements:
pip install -r requirements.txt -U --break-system-packages
--break-system-packages is required on linux since accessible_output2 will attempt to use speech-dispatcher bindings for speech output. These bindings are, to the best of my knowledge, not installable through pip, which appears to be the only obstacle to running in a venv. Yes, you read that right, never run that pip invocation under sudo, which will essentially eat your system for lunch!

Running server.py doesn't require any package.

The optional upnpclient package can help for the configuration of your router.

Running soundrts.py requires:
* pygame
* accessible_output2

Building a package requires also:
* docutils
* cx_Freeze

Testing requires:
* pytest

Official SoundRTS web site: http://jlpo.free.fr/soundrts
