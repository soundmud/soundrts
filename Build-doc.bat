@echo off

c:\python25\python.exe soundrts/rules2doc.py
if errorlevel 1 pause

cd doc\src

c:\python25\python.exe ../buildhtml.py
if errorlevel 1 pause

rename *.html *.htm
if errorlevel 1 pause

move *.htm ..\en
if errorlevel 1 pause

start ..\en\help-index.htm

cd ..\..