@echo off
setlocal enableextensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SENTINELTRAY_ROOT=%ROOT%"

set "PYTHON=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

start /MIN "SentinelTray" "%PYTHON%" "%ROOT%\main.py" %*
exit /b 0
