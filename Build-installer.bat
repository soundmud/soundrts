@echo off

set /p MyAppVer= <version.txt
if errorlevel 1 goto fin

del %TEMP%\soundrts\dist\soundrts-%MyAppVer%.zip
"c:\program files\7-zip\7z" a -tzip %TEMP%\soundrts\dist\soundrts-%MyAppVer%.zip %TEMP%\soundrts\build\soundrts-%MyAppVer% -r
if errorlevel 1 goto fin

"c:\program files (x86)\inno setup 5\compil32" /cc %TEMP%\soundrts\build\soundrts.iss
if errorlevel 1 goto fin

del %TEMP%\soundrts\dist\soundrts-%MyAppVer%-windows.zip
"c:\program files\7-zip\7z" a -tzip %TEMP%\soundrts\dist\soundrts-%MyAppVer%-windows.zip %TEMP%\soundrts\build\soundrts-%MyAppVer%-windows -r
if errorlevel 1 goto fin

:fin
if errorlevel 1 pause
