@echo off
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%prepare_portable_runtime.ps1" %*
exit /b %ERRORLEVEL%
