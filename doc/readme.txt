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

- install Python 2.7 (probably already done):
sudo apt-get install python2.7

- install Pygame for Python 2.7:
sudo apt-get install python-pygame

- to run the client:
cd soundrts
python2.7 soundrts.py


1.2 Mac

- unzip the file in the folder of your choice.
- install Python 2.7
- install Pygame for Python 2.7: http://www.pygame.org/download.shtml
- to run the client, launch soundrts.py

1.3 Windows

- unzip the file in the folder of your choice.
- install Python 2.7: http://www.python.org/ftp/python/2.7.6/python-2.7.6.msi
- install Pygame for Python 2.7: http://pygame.org/ftp/pygame-1.9.1.win32-py2.7.msi
- install pywin32 (to use SAPI 5, the default): http://sourceforge.net/projects/pywin32/files/pywin32/Build%20218/pywin32-218.win32-py2.7.exe/download

- to run the client, double-click on soundrts.py

If you want to use your screen reader:
- copy ScreenReaderAPI.dll and nvdaControllerClient.dll from http://forum.audiogames.net/viewtopic.php?id=6222 to the folder of soundrts.py
- edit SoundRTS.ini: srapi = 1

2. Server

To start a standalone server from the command line (no sound support needed), launch server.pyc . Kill the process when you are done.
A log file called SoundRTS-server.log will be written in a temporary folder or in the game folder.


3. Manual

The manual is in the file called help-index.htm