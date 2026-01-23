@echo off
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%package_portable.ps1" %*
exit /b %ERRORLEVEL%
