@echo off

c:\Python25\python.exe -m cProfile -o %tmp%\clientprof soundrts.py

c:\Python25\python.exe profile-read.py

:fin
if errorlevel 1 pause
