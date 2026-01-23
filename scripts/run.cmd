@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON_RUNTIME=%ROOT%\runtime\python\python.exe"
set "CHECKSUMS=%ROOT%\runtime\checksums.txt"
set "PYTHON_VENV=%ROOT%\.venv\Scripts\python.exe"
set "SENTINELTRAY_ROOT=%ROOT%"
set "SENTINELTRAY_DATA_DIR=%ROOT%\UserData"
set "LOCAL_CONFIG=%SENTINELTRAY_DATA_DIR%\config.local.yaml"
set "LOG_DIR=%SENTINELTRAY_DATA_DIR%\logs\scripts"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\run_%LOG_TS%.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\run_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

call :log "INFO" "Iniciando run.cmd"
set "PYTHON="
if exist "%PYTHON_RUNTIME%" if exist "%CHECKSUMS%" set "PYTHON=%PYTHON_RUNTIME%"
if "%PYTHON%"=="" if exist "%PYTHON_VENV%" set "PYTHON=%PYTHON_VENV%"
if "%PYTHON%"=="" set "PYTHON=python"
set "USE_POWERSHELL=0"

if "%PYTHON%"=="%PYTHON_RUNTIME%" (
  rem usando runtime empacotado
) else (
  if not exist "%PYTHON_RUNTIME%" call :log "WARN" "Runtime nao encontrado; usando Python alternativo."
  if exist "%PYTHON_RUNTIME%" if not exist "%CHECKSUMS%" call :log "WARN" "Checksums ausente; usando Python alternativo."
)
if "%PYTHON%"=="%PYTHON_VENV%" (
  where powershell >nul 2>nul
  if not errorlevel 1 set "USE_POWERSHELL=1"
)
call :log_context

if not exist "%LOCAL_CONFIG%" (
  call :log "ERROR" "Configuração local não encontrada: %LOCAL_CONFIG%"
  echo Configuração local não encontrada.
  echo Arquivo esperado: %LOCAL_CONFIG%
  echo Crie o arquivo a partir de templates\local\config.local.yaml e tente novamente.
  exit /b 1
)
for %%I in ("%LOCAL_CONFIG%") do set "CFG_SIZE=%%~zI"
if "%CFG_SIZE%"=="0" (
  call :log "ERROR" "Configuração local vazia: %LOCAL_CONFIG%"
  echo Configuração local vazia.
  echo Arquivo: %LOCAL_CONFIG%
  echo Preencha os campos obrigatórios e tente novamente.
  exit /b 1
)

if "%USERPROFILE%"=="" (
  rem USERPROFILE nao e necessario em modo portable.
)

if "%USE_POWERSHELL%"=="1" (
  call :log "INFO" "Ativando venv via PowerShell"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%ROOT%\.venv\Scripts\Activate.ps1'; python '%ROOT%\main.py' %*"
) else (
  "%PYTHON%" "%ROOT%\main.py" %*
)
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
