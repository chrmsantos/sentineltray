@echo off
setlocal enableextensions

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\runtime\python\python.exe"
set "CHECKSUMS=%ROOT%\runtime\checksums.txt"

if not exist "%PYTHON%" (
  echo Runtime nao encontrado. Execute scripts\bootstrap_self_contained.cmd primeiro.
  exit /b 1
)

if not exist "%CHECKSUMS%" (
  echo Runtime incompleto. Reexecute scripts\bootstrap_self_contained.cmd.
  exit /b 1
)

if "%USERPROFILE%"=="" (
  echo USERPROFILE nao definido. Abra uma sessao de usuario Windows valida.
  exit /b 1
)

"%PYTHON%" "%ROOT%\main.py" %*
