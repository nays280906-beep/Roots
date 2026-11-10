@echo off
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && (py -3 --version >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && (python --version >nul 2>nul && set "PY=python"))
if not defined PY goto nopy
start "ROOTS server" /min cmd /c "%PY% server.py --open none"
timeout /t 2 /nobreak >nul
set "BR="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BR=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BR if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BR=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BR if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BR=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BR if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BR=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if defined BR goto launch
echo Edge/Chrome not found in the usual place. Opening your default browser instead; click the page once to go full screen.
start "" "http://127.0.0.1:8765/student?fs=1"
exit /b 0
:launch
start "" "%BR%" --app=http://127.0.0.1:8765/student --start-fullscreen
exit /b 0

:nopy
echo.
echo  Python 3 was not found on this laptop.
echo  Install it once from https://www.python.org/downloads/  (needs internet only for this step)
echo  and TICK the box "Add python.exe to PATH" in the installer. Then run this file again.
echo.
pause
exit /b 1
