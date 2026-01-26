@echo off
setlocal
set "ROOT=%~dp0"
call "%ROOT%scripts\run.cmd" /background
exit /b %ERRORLEVEL%
