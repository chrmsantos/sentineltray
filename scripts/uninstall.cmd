@echo off
setlocal enableextensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

call "%ROOT%\install.cmd" /uninstall
