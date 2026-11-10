@echo off
rem Stops a ROOTS server that was started minimised by Start_Student_Fullscreen.bat.
rem (If you used Start_ROOTS.bat or Start_SideBySide.bat, just close that black window.)
taskkill /fi "WINDOWTITLE eq ROOTS server*" /t /f >nul 2>nul
echo ROOTS server stopped (if it was running).
timeout /t 2 >nul
