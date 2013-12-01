@echo off

@rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py --only rtsworld.py --no-shadowbuiltin
rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 50 clientmain.py servermain.py world.py mapfile.py
@rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -eerror clientmain.py servermain.py
rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 clientgame.py
C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 soundrts/worldunit.py
rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 world.py
rem C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 worldplayer.py
C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 soundrts/worldentity.py
C:\Python25\python.exe C:\Python25\Lib\site-packages\pychecker\checker.py -q --limit 500 soundrts/clientworld.py

pause
