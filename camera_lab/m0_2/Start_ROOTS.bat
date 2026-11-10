@echo off
title ROOTS server - keep this window open
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && (py -3 --version >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && (python --version >nul 2>nul && set "PY=python"))
if not defined PY goto nopy
%PY% server.py --open home
if errorlevel 1 pause
exit /b 0

:nopy
echo.
echo  Python 3 was not found on this laptop.
echo  Install it once from https://www.python.org/downloads/  (needs internet only for this step)
echo  and TICK the box "Add python.exe to PATH" in the installer. Then run this file again.
echo.
pause
exit /b 1
