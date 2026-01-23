@echo off
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
powershell -NoProfile -ExecutionPolicy Bypass -NoExit -Command "& '%ROOT%\.venv\Scripts\Activate.ps1'"
exit /b %ERRORLEVEL%
