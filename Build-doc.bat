@echo off

python.exe rules2doc.py
if errorlevel 1 pause

cd doc\src

python.exe ../buildhtml.py
if errorlevel 1 pause

rename *.html *.htm
if errorlevel 1 pause

rd /S /Q %TEMP%\soundrts\build\doc
mkdir %TEMP%\soundrts\build\doc
move *.htm %TEMP%\soundrts\build\doc
if errorlevel 1 pause

copy ..\es\*.* %TEMP%\soundrts\build\doc
copy ..\it\*.* %TEMP%\soundrts\build\doc

start %TEMP%\soundrts\build\doc\help-index.htm

cd ..\..