@echo off
setlocal enableextensions enabledelayedexpansion

rem SentinelTray installer (standalone)

set "ROOT=%~dp0"
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "DEFAULT_INSTALL_DIR=%USERPROFILE%\AxonZ\SystemData\sentineltray"
set "INSTALL_DIR=%DEFAULT_INSTALL_DIR%"
set "OFFLINE=0"
set "ZIP_PATH="
set "ZIP_URL=https://github.com/AxonZ/sentineltray/releases/latest/download/sentineltray-self-contained.zip"
set "SHA256="
set "DO_UPDATE=0"
set "DO_UNINSTALL=0"
set "NO_DESKTOP=0"
set "NO_STARTMENU=0"

set "LOG_DIR=%TEMP%\sentineltray-install"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\install_%LOG_TS%.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\install_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

call :log "INFO" "Iniciando instalacao"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="/offline" set "OFFLINE=1"
if /I "%~1"=="/zip" (shift & set "ZIP_PATH=%~1")
if /I "%~1"=="/dir" (shift & set "INSTALL_DIR=%~1")
if /I "%~1"=="/sha256" (shift & set "SHA256=%~1")
if /I "%~1"=="/update" set "DO_UPDATE=1"
if /I "%~1"=="/uninstall" set "DO_UNINSTALL=1"
if /I "%~1"=="/no-desktop" set "NO_DESKTOP=1"
if /I "%~1"=="/no-startmenu" set "NO_STARTMENU=1"
shift
goto parse_args

:args_done
call :log_context

if "%DO_UNINSTALL%"=="1" (
	call :uninstall
	exit /b 0
)

if "%ZIP_PATH%"=="" set "ZIP_PATH=%LOG_DIR%\sentineltray_%LOG_TS%.zip"
set "WORK_DIR=%LOG_DIR%\work_%LOG_TS%"
set "BACKUP_DIR="

if "%OFFLINE%"=="1" (
	if not exist "%ZIP_PATH%" (
		call :fail "Zip offline nao encontrado: %ZIP_PATH%"
	)
) else (
	call :log "INFO" "Baixando pacote: %ZIP_URL%"
	powershell -NoProfile -Command "Invoke-WebRequest -Uri '%ZIP_URL%' -OutFile '%ZIP_PATH%' -UseBasicParsing" || call :fail "Falha ao baixar pacote"
)

if not "%SHA256%"=="" call :validate_hash "%ZIP_PATH%" "%SHA256%"

if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%" || call :fail "Falha ao criar pasta temporaria"

call :log "INFO" "Extraindo pacote"
powershell -NoProfile -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%WORK_DIR%' -Force" || call :fail "Falha ao extrair pacote"

for /f "delims=" %%I in ('powershell -NoProfile -Command "(Get-ChildItem -Directory -Path '%WORK_DIR%' | Select-Object -First 1).FullName"') do set "SOURCE_DIR=%%I"
if "%SOURCE_DIR%"=="" call :fail "Conteudo do pacote invalido"

if "%DO_UPDATE%"=="1" (
	if exist "%INSTALL_DIR%" (
		set "BACKUP_DIR=%INSTALL_DIR%_backup_%LOG_TS%"
		call :log "INFO" "Criando backup: %BACKUP_DIR%"
		move "%INSTALL_DIR%" "%BACKUP_DIR%" >nul || call :fail "Falha ao criar backup"
	)
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" || call :fail "Falha ao criar diretorio de instalacao"

call :log "INFO" "Copiando arquivos para %INSTALL_DIR%"
powershell -NoProfile -Command "Copy-Item -Path '%SOURCE_DIR%\*' -Destination '%INSTALL_DIR%' -Recurse -Force" || call :fail "Falha ao copiar arquivos"

if not exist "%INSTALL_DIR%\runtime\checksums.txt" call :fail "Runtime ausente (checksums.txt nao encontrado)"
if not exist "%INSTALL_DIR%\runtime\python\python.exe" call :fail "Runtime ausente (python.exe nao encontrado)"

if exist "%INSTALL_DIR%\scripts\bootstrap_self_contained.cmd" (
	call "%INSTALL_DIR%\scripts\bootstrap_self_contained.cmd"
	if errorlevel 1 call :fail "Runtime invalido"
) else (
	call :fail "bootstrap_self_contained.cmd ausente"
)

if not exist "%INSTALL_DIR%\scripts\create_shortcut.ps1" call :fail "create_shortcut.ps1 ausente"

if not exist "%INSTALL_DIR%\UserData" mkdir "%INSTALL_DIR%\UserData" >nul 2>nul
if not exist "%INSTALL_DIR%\UserData\config.local.yaml" (
	if exist "%INSTALL_DIR%\templates\local\config.local.yaml" (
		copy /y "%INSTALL_DIR%\templates\local\config.local.yaml" "%INSTALL_DIR%\UserData\config.local.yaml" >nul
	)
)

call :log "INFO" "Criando atalhos"
set "PS_ARGS=-InstallDir \"%INSTALL_DIR%\" -LogPath \"%LOG_FILE%\""
if "%NO_DESKTOP%"=="0" set "PS_ARGS=%PS_ARGS% -CreateDesktop"
if "%NO_STARTMENU%"=="0" set "PS_ARGS=%PS_ARGS% -CreateStartMenu"
powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\scripts\create_shortcut.ps1" %PS_ARGS% || call :fail "Falha ao criar atalhos"

call :log "INFO" "Instalacao concluida"
exit /b 0

:uninstall
call :log "INFO" "Desinstalando"
if exist "%INSTALL_DIR%" (
	rmdir /s /q "%INSTALL_DIR%" >nul 2>nul
)

powershell -NoProfile -Command "$desktop=[Environment]::GetFolderPath('Desktop'); if ($desktop) { Remove-Item -LiteralPath (Join-Path $desktop 'SentinelTray.lnk') -Force -ErrorAction SilentlyContinue }" >nul 2>nul
powershell -NoProfile -Command "$programs=[Environment]::GetFolderPath('Programs'); if ($programs) { Remove-Item -LiteralPath (Join-Path $programs 'SentinelTray.lnk') -Force -ErrorAction SilentlyContinue }" >nul 2>nul
call :log "INFO" "Desinstalacao concluida"
exit /b 0

:validate_hash
set "HASH_FILE=%~1"
set "EXPECTED=%~2"
if "%EXPECTED%"=="" exit /b 0
call :log "INFO" "Validando SHA256 do pacote"
powershell -NoProfile -Command "$expected='%EXPECTED%'.ToLower(); $actual=(Get-FileHash -Algorithm SHA256 -Path '%HASH_FILE%').Hash.ToLower(); if ($actual -ne $expected) { exit 1 }" || call :fail "SHA256 invalido"
call :log "INFO" "SHA256 ok"
exit /b 0

:rollback
if "%BACKUP_DIR%"=="" exit /b 0
call :log "WARN" "Executando rollback"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" >nul 2>nul
move "%BACKUP_DIR%" "%INSTALL_DIR%" >nul 2>nul
exit /b 0

:fail
set "MESSAGE=%~1"
if "%MESSAGE%"=="" set "MESSAGE=Falha inesperada"
call :log "ERROR" "%MESSAGE%"
call :rollback
exit /b 1

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
call :log "INFO" "InstallDir: %INSTALL_DIR%"
call :log "INFO" "Offline: %OFFLINE%"
call :log "INFO" "ZipPath: %ZIP_PATH%"
call :log "INFO" "ZipUrl: %ZIP_URL%"
call :log "INFO" "Update: %DO_UPDATE%"
call :log "INFO" "NoDesktop: %NO_DESKTOP%"
call :log "INFO" "NoStartMenu: %NO_STARTMENU%"
for /f %%I in ('ver') do call :log "INFO" "OS: %%I"
for /f %%I in ('powershell -NoProfile -Command "$PSVersionTable.PSVersion.ToString()"') do call :log "INFO" "PowerShell: %%I"
exit /b 0
