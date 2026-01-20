@echo off
setlocal enableextensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\runtime\python\python.exe"

if not exist "%PYTHON%" (
  echo Runtime nao encontrado. Execute scripts\bootstrap_self_contained.cmd primeiro.
  exit /b 1
)

"%PYTHON%" "%ROOT%\main.py" %*
