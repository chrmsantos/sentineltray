@echo off
setlocal enableextensions enabledelayedexpansion

rem Bootstrap self-contained runtime (embedded CPython + offline wheels)

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\runtime"
set "PY_VERSION=3.11.9"
set "PY_EMBED_ZIP=%RUNTIME_DIR%\python-embed.zip"
set "PY_DIR=%RUNTIME_DIR%\python"
set "PIP_SCRIPT=%RUNTIME_DIR%\get-pip.py"
set "WHEEL_DIR=%RUNTIME_DIR%\wheels"
set "LOCK_FILE=%ROOT%\requirements.lock"

if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%" || exit /b 1

call :log "Baixando CPython embutido %PY_VERSION%"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-embed-amd64.zip' -OutFile '%PY_EMBED_ZIP%'" || exit /b 1

if exist "%PY_DIR%" rmdir /s /q "%PY_DIR%"
mkdir "%PY_DIR%" || exit /b 1
powershell -NoProfile -Command "Expand-Archive -Path '%PY_EMBED_ZIP%' -DestinationPath '%PY_DIR%' -Force" || exit /b 1

call :log "Baixando get-pip"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PIP_SCRIPT%'" || exit /b 1

call :log "Habilitando site-packages"
for %%F in ("%PY_DIR%\python*._pth") do set "PTH_FILE=%%~fF"
if not defined PTH_FILE exit /b 1
powershell -NoProfile -Command "(Get-Content -Path '%PTH_FILE%') | ForEach-Object { $_ -replace '^#?import site','import site' } | Set-Content -Path '%PTH_FILE%'" || exit /b 1
powershell -NoProfile -Command "if (-not (Select-String -Path '%PTH_FILE%' -Pattern 'Lib\\site-packages')) { Add-Content -Path '%PTH_FILE%' -Value 'Lib\\site-packages' }" || exit /b 1

call :log "Instalando pip no runtime"
"%PY_DIR%\python.exe" "%PIP_SCRIPT%" --no-warn-script-location || exit /b 1

if not exist "%LOCK_FILE%" exit /b 1
if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%" || exit /b 1

call :log "Baixando wheels offline"
"%PY_DIR%\python.exe" -m pip download -r "%LOCK_FILE%" -d "%WHEEL_DIR%" --only-binary=:all: || exit /b 1

call :log "Instalando dependencias do wheelhouse"
"%PY_DIR%\python.exe" -m pip install --no-index --find-links "%WHEEL_DIR%" -r "%LOCK_FILE%" || exit /b 1

call :log "Runtime pronto"
exit /b 0

:log
echo [%DATE% %TIME%] %*
exit /b 0
