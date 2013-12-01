1. Installation
1.1 Linux
1.2 Mac
1.3 Windows
2. Server
3. Manual

*************************


1. Installation

1.1 Linux

The examples are given for Debian based distributions.

- unzip the file in the folder of your choice, for example your home directory:
unzip soundrts.zip

- if you want or need to use Python 2.7, rename the soundrts folder to soundrts_old and the soundrts_python27 folder to soundrts

- install Python 2.5:
sudo apt-get install python2.5

- install Pygame for Python 2.5:
sudo apt-get install python-pygame

- to run the client:
cd soundrts
python2.5 soundrts.pyc


1.2 Mac

- unzip the file in the folder of your choice.

- if you want or need to use Python 2.7, rename the soundrts folder to soundrts_old and the soundrts_python27 folder to soundrts

- install Python 2.5

- install Pygame for Python 2.5: http://www.pygame.org/download.shtml

- to run the client, launch soundrts.pyc

1.3 Windows

- unzip the file in the folder of your choice.
- if you want or need to use Python 2.7, rename the soundrts folder to soundrts_old and the soundrts_python27 folder to soundrts
- install Python 2.5 http://www.python.org/download/releases/2.5.2
- install Pygame for Python 2.5: http://www.pygame.org/download.shtml

- to run the client, double-click on soundrts.pyc

If you want to use your screen reader:
- copy ScreenReaderAPI.dll and nvdaControllerClient.dll from http://forum.audiogames.net/viewtopic.php?id=6222 to the folder of soundrts.py
- edit SoundRTS.ini: srapi = 1

2. Server

To start a standalone server from the command line (no sound support needed), launch server.pyc . Kill the process when you are done.
A log file called SoundRTS-server.log will be written in a temporary folder or in the game folder.


3. Manual

The manual is in the file called help-index.htm