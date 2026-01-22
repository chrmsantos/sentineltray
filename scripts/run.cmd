@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\runtime\python\python.exe"
set "CHECKSUMS=%ROOT%\runtime\checksums.txt"
set "SENTINELTRAY_ROOT=%ROOT%"
set "SENTINELTRAY_DATA_DIR=%ROOT%\UserData"
set "LOG_DIR=%SENTINELTRAY_DATA_DIR%\logs\scripts"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\run_%LOG_TS%.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\run_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 10 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

call :log "INFO" "Iniciando run.cmd"
call :log_context

if not exist "%PYTHON%" (
  call :log "ERROR" "Runtime nao encontrado."
  echo Runtime nao encontrado.
  exit /b 1
)

if not exist "%CHECKSUMS%" (
  call :log "ERROR" "Runtime incompleto."
  echo Runtime incompleto.
  exit /b 1
)

if "%USERPROFILE%"=="" (
  rem USERPROFILE nao e necessario em modo portable.
)

"%PYTHON%" "%ROOT%\main.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
call :log "INFO" "Processo finalizado com exit code !EXIT_CODE!"
exit /b !EXIT_CODE!

:log
set "LEVEL=%~1"
set "MESSAGE=%~2"
if /I "%LEVEL%"=="INFO" goto log_known
if /I "%LEVEL%"=="WARN" goto log_known
if /I "%LEVEL%"=="ERROR" goto log_known
if /I "%LEVEL%"=="DEBUG" goto log_known
set "LEVEL=INFO"
set "MESSAGE=%*"
:log_known
echo [%DATE% %TIME%] [%LEVEL%] %MESSAGE%
>>"%LOG_FILE%" echo [%DATE% %TIME%] [%LEVEL%] %MESSAGE%
exit /b 0

:log_context
call :log "INFO" "Root: %ROOT%"
call :log "INFO" "Python: %PYTHON%"
call :log "INFO" "Checksums: %CHECKSUMS%"
call :log "INFO" "DataDir: %SENTINELTRAY_DATA_DIR%"
for /f %%I in ('ver') do call :log "INFO" "OS: %%I"
for /f %%I in ('powershell -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"') do call :log "INFO" "PowerShell: %%I"
exit /b 0
