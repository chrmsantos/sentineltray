@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_named_exe.ps1"
exit /b %ERRORLEVEL%
