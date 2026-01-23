@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "STARTUP_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "STARTUP_NAME=SentinelTray"
set "PYTHON_RUNTIME=%ROOT%\runtime\python\python.exe"
set "CHECKSUMS=%ROOT%\runtime\checksums.txt"
set "PYTHON_VENV=%ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_WHEELS=%ROOT%\runtime\wheels"
set "DEPS_MARKER=%ROOT%\runtime\.deps_ready"
if "%SENTINELTRAY_WHEEL_DIR%"=="" set "SENTINELTRAY_WHEEL_DIR=%RUNTIME_WHEELS%"
if "%SENTINELTRAY_DEPS_MARKER%"=="" set "SENTINELTRAY_DEPS_MARKER=%DEPS_MARKER%"
set "SENTINELTRAY_ROOT=%ROOT%"
set "SENTINELTRAY_DATA_DIR=%ROOT%\config"
if "%SENTINELTRAY_PORTABLE%"=="" set "SENTINELTRAY_PORTABLE=1"
if "%SENTINELTRAY_CONFIG_ENCRYPTION%"=="" set "SENTINELTRAY_CONFIG_ENCRYPTION=portable"
set "LOCAL_CONFIG=%SENTINELTRAY_DATA_DIR%\config.local.yaml"
set "LOCAL_CONFIG_ENC=%SENTINELTRAY_DATA_DIR%\config.local.yaml.enc"
set "LOG_DIR=%SENTINELTRAY_DATA_DIR%\logs\scripts"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\run_%LOG_TS%.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\run_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

if /I "%~1"=="/install-startup" goto install_startup
if /I "%~1"=="/remove-startup" goto remove_startup
if /I "%~1"=="/startup-status" goto startup_status
set "RUN_FOREGROUND=0"
if /I "%~1"=="/foreground" (
  set "RUN_FOREGROUND=1"
  shift
)
if /I "%~1"=="/background" (
  set "RUN_FOREGROUND=0"
  shift
)

call :log "INFO" "Starting run.cmd"
set "PYTHON="
set "PYTHONW="
if exist "%PYTHON_RUNTIME%" if exist "%CHECKSUMS%" set "PYTHON=%PYTHON_RUNTIME%"
if "%PYTHON%"=="" if exist "%PYTHON_VENV%" set "PYTHON=%PYTHON_VENV%"
if "%PYTHON%"=="" set "PYTHON=python"
set "USE_POWERSHELL=0"

if /I "%SENTINELTRAY_PORTABLE%"=="1" (
  if not exist "%PYTHON_RUNTIME%" (
    call :log "ERROR" "Portable mode requires runtime\python."
    echo Portable mode requires runtime\python.
    exit /b 1
  )
)

if "%PYTHON%"=="%PYTHON_RUNTIME%" (
  rem using bundled runtime
  if exist "%ROOT%\runtime\python\pythonw.exe" set "PYTHONW=%ROOT%\runtime\python\pythonw.exe"
  if not exist "%DEPS_MARKER%" (
    call :bootstrap_deps
    if errorlevel 1 exit /b 1
  )
) else (
  if not exist "%PYTHON_RUNTIME%" call :log "WARN" "Runtime not found; using alternate Python."
  if exist "%PYTHON_RUNTIME%" if not exist "%CHECKSUMS%" call :log "WARN" "Checksums missing; using alternate Python."
)
if "%PYTHON%"=="%PYTHON_VENV%" (
  where powershell >nul 2>nul
  if not errorlevel 1 set "USE_POWERSHELL=1"
  if exist "%ROOT%\.venv\Scripts\pythonw.exe" set "PYTHONW=%ROOT%\.venv\Scripts\pythonw.exe"
)
if "%PYTHONW%"=="" if not "%PYTHON%"=="python" set "PYTHONW=%PYTHON%"
if "%PYTHONW%"=="" set "PYTHONW=pythonw"
call :log_context

if not exist "%LOCAL_CONFIG%" if not exist "%LOCAL_CONFIG_ENC%" (
  call :log "ERROR" "Local configuration not found: %LOCAL_CONFIG%"
  echo Local configuration not found.
  echo Expected file: %LOCAL_CONFIG%
  echo Or encrypted file: %LOCAL_CONFIG_ENC%
  echo Create it from templates\local\config.local.yaml and try again.
  exit /b 1
)
set "CFG_SIZE=0"
if exist "%LOCAL_CONFIG%" for %%I in ("%LOCAL_CONFIG%") do set "CFG_SIZE=%%~zI"
if exist "%LOCAL_CONFIG%" (
  if "%CFG_SIZE%"=="0" (
    call :log "ERROR" "Local configuration is empty: %LOCAL_CONFIG%"
    echo Local configuration is empty.
    echo File: %LOCAL_CONFIG%
    echo Fill the required fields and try again.
    exit /b 1
  )
)

if "%USERPROFILE%"=="" (
  rem USERPROFILE is not required in portable mode.
)

if "%RUN_FOREGROUND%"=="1" (
  if "%USE_POWERSHELL%"=="1" (
    call :log "INFO" "Activating venv via PowerShell"
    call :log "INFO" "Application running (foreground mode). Use Ctrl+C to stop."
    echo SentinelTray is running. Use Ctrl+C to stop.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%ROOT%\.venv\Scripts\Activate.ps1'; python '%ROOT%\main.py' %*"
  ) else (
    call :log "INFO" "Application running (foreground mode). Use Ctrl+C to stop."
    echo SentinelTray is running. Use Ctrl+C to stop.
    "%PYTHON%" "%ROOT%\main.py" %*
  )
  set "EXIT_CODE=%ERRORLEVEL%"
  call :log "INFO" "Process finished with exit code !EXIT_CODE!"
  exit /b !EXIT_CODE!
)

call :log "INFO" "Launching background process"
start "" "%PYTHONW%" "%ROOT%\main.py" %*
exit /b 0

:bootstrap_deps
if not exist "%RUNTIME_WHEELS%" (
  call :log "ERROR" "Wheel directory missing: %RUNTIME_WHEELS%"
  echo Missing wheels in %RUNTIME_WHEELS%.
  exit /b 1
)
call :log "INFO" "Bootstrapping runtime dependencies"
"%PYTHON%" "%ROOT%\scripts\bootstrap_runtime.py"
if errorlevel 1 (
  call :log "ERROR" "Dependency bootstrap failed"
  exit /b 1
)
call :log "INFO" "Dependency bootstrap complete"
exit /b 0

:install_startup
call :log "INFO" "Installing startup entry"
set "STARTUP_CMD=\"%ROOT%\scripts\run.cmd\" /background"
reg add "%STARTUP_KEY%" /v "%STARTUP_NAME%" /t REG_SZ /d "%STARTUP_CMD%" /f >nul 2>nul
if errorlevel 1 (
  call :log "ERROR" "Failed to install startup entry"
  echo Failed to install startup entry.
  exit /b 1
)
call :log "INFO" "Startup entry installed"
echo Startup entry installed.
exit /b 0

:remove_startup
call :log "INFO" "Removing startup entry"
reg delete "%STARTUP_KEY%" /v "%STARTUP_NAME%" /f >nul 2>nul
if errorlevel 1 (
  call :log "WARN" "Startup entry not found or could not be removed"
  echo Startup entry not found or could not be removed.
  exit /b 1
)
call :log "INFO" "Startup entry removed"
echo Startup entry removed.
exit /b 0

:startup_status
reg query "%STARTUP_KEY%" /v "%STARTUP_NAME%" >nul 2>nul
if errorlevel 1 (
  echo Startup entry not installed.
  exit /b 1
)
echo Startup entry installed.
exit /b 0

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
