@echo off
setlocal enableextensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "SENTINELTRAY_ROOT=%ROOT%"

set "PYTHON=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

echo SentinelTray is running. Use Ctrl+C to stop.
"%PYTHON%" "%ROOT%\main.py" %*
exit /b %ERRORLEVEL%
