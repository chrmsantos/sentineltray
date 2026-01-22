@echo off
setlocal enableextensions enabledelayedexpansion

rem SentinelTray installer (Windows CMD)
rem Licencas: Python (PSF), pip (PSF), GitHub (terms), dependencias via requirements.txt.
rem O usuario deve revisar as licencas antes de instalar.

set "REPO_URL=https://github.com/chrmsantos/sentineltray/archive/refs/heads/master.zip"
set "INSTALL_DIR=%USERPROFILE%\AxonZ\SystemData\sentineltray"
set "TEMP_ZIP=%TEMP%\sentineltray.zip"
set "EXTRACT_DIR=%TEMP%\sentineltray-extract"
set "LOG_DIR=%TEMP%\sentineltray-install"
set "USER_DATA_DIR=%USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData"
set "REPO_SHA256="
set "MODE=install"
set "OFFLINE=0"
set "ZIP_PATH="
set "CREATE_DESKTOP=1"
set "CREATE_START_MENU=1"
set "START_MENU_NAME=SentinelTray"
set "DOWNLOADED_ZIP=0"

:parse
if "%~1"=="" goto parsed
if /I "%~1"=="/offline" set "OFFLINE=1"
if /I "%~1"=="/zip" set "ZIP_PATH=%~2" & shift
if /I "%~1"=="/dir" call :log "Parametro /dir ignorado; instalacao fixa em %INSTALL_DIR%" & shift
if /I "%~1"=="/update" set "MODE=update"
if /I "%~1"=="/uninstall" set "MODE=uninstall"
if /I "%~1"=="/no-desktop" set "CREATE_DESKTOP=0"
if /I "%~1"=="/no-startmenu" set "CREATE_START_MENU=0"
if /I "%~1"=="/sha256" set "REPO_SHA256=%~2" & shift
shift
goto parse
:parsed

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\install_%LOG_TS%.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\install_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

call :log "Iniciando instalacao do SentinelTray"
call :check_powershell
call :remove_autostart_legacy

if /I "%MODE%"=="uninstall" goto uninstall

if /I "%MODE%"=="update" (
	if not exist "%INSTALL_DIR%" (
		call :log "Instalacao anterior nao encontrada; usando modo install"
		set "MODE=install"
	)
)

call :log "Destino: %INSTALL_DIR%"
call :ensure_install_dir
call :check_write
call :check_disk

if "%OFFLINE%"=="1" (
	if "%ZIP_PATH%"=="" call :fail "Modo offline requer /zip <caminho>"
	set "TEMP_ZIP=%ZIP_PATH%"
	call :log "Modo offline: usando zip local %TEMP_ZIP%"
) else (
	if not "%ZIP_PATH%"=="" (
		set "TEMP_ZIP=%ZIP_PATH%"
		call :log "Usando zip local %TEMP_ZIP%"
	) else (
		call :log "Baixando codigo do GitHub"
		powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%TEMP_ZIP%'" || call :fail "Falha ao baixar o pacote do GitHub"
		set "DOWNLOADED_ZIP=1"
	)
)

if not exist "%TEMP_ZIP%" call :fail "Arquivo zip nao encontrado"
call :validate_hash

call :log "Extraindo arquivos"
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%" || call :fail "Falha ao preparar diretorio temporario"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%EXTRACT_DIR%' -Force" || call :fail "Falha ao extrair o pacote"

set "SRC_DIR="
for /d %%D in ("%EXTRACT_DIR%\sentineltray-*") do set "SRC_DIR=%%D"
if not defined SRC_DIR call :fail "Diretorio de origem nao encontrado"

set "BACKUP_DIR="
if /I "%MODE%"=="update" (
	if exist "%INSTALL_DIR%" (
		set "BACKUP_DIR=%TEMP%\sentineltray-backup\sentineltray_%LOG_TS%"
		call :log "Criando backup: %BACKUP_DIR%"
		powershell -NoProfile -Command "New-Item -ItemType Directory -Path '%TEMP%\sentineltray-backup' -Force | Out-Null; Move-Item -Path '%INSTALL_DIR%' -Destination '%BACKUP_DIR%'" || call :fail "Falha ao criar backup"
	)
)

call :log "Copiando arquivos do projeto"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" || call :fail "Nao foi possivel criar diretorio de instalacao"
powershell -NoProfile -Command "Copy-Item -Path '%SRC_DIR%\*' -Destination '%INSTALL_DIR%' -Recurse -Force" || (call :rollback & call :fail "Falha ao copiar arquivos")

cd /d "%INSTALL_DIR%" || (call :rollback & call :fail "Falha ao acessar diretorio de instalacao")

call :log "Preparando runtime auto-contido"
call "%INSTALL_DIR%\scripts\bootstrap_self_contained.cmd" || (call :rollback & call :fail "Falha ao preparar runtime")

call :log "Copiando config.local.yaml (se necessario)"
call :copy_config

call :log "Criando atalhos"
set "SHORTCUT_FLAGS="
if "%CREATE_DESKTOP%"=="1" set "SHORTCUT_FLAGS=!SHORTCUT_FLAGS! -CreateDesktop"
if "%CREATE_START_MENU%"=="1" set "SHORTCUT_FLAGS=!SHORTCUT_FLAGS! -CreateStartMenu"
if not "%SHORTCUT_FLAGS%"=="" (
	powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%\scripts\create_shortcut.ps1" -InstallDir "%INSTALL_DIR%" %SHORTCUT_FLAGS% -StartMenuName "%START_MENU_NAME%" || (call :rollback & call :fail "Falha ao criar atalhos")
) else (
	call :log "Atalhos desativados por parametro"
)

call :log "Limpando arquivos temporarios"
if "%DOWNLOADED_ZIP%"=="1" if exist "%TEMP_ZIP%" del /f /q "%TEMP_ZIP%" >nul 2>nul
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%" >nul 2>nul

if not "%BACKUP_DIR%"=="" if exist "%BACKUP_DIR%" rmdir /s /q "%BACKUP_DIR%" >nul 2>nul

call :log "Instalacao concluida"
echo Instalacao concluida.
echo Execute: %INSTALL_DIR%\scripts\run.cmd
exit /b 0

:uninstall
call :log "Iniciando desinstalacao"
call :remove_autostart_legacy
call :remove_shortcuts
if exist "%INSTALL_DIR%" (
	rmdir /s /q "%INSTALL_DIR%" || call :fail "Falha ao remover diretorio de instalacao"
) else (
	call :log "Diretorio de instalacao nao encontrado"
)
call :log "Desinstalacao concluida"
echo Desinstalacao concluida.
exit /b 0

:check_powershell
where powershell >nul 2>nul || call :fail "PowerShell nao encontrado"
powershell -NoProfile -Command "$null = New-Object -ComObject WScript.Shell" || call :fail "Falha ao inicializar COM (WScript.Shell)"
exit /b 0

:ensure_install_dir
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" || call :fail "Nao foi possivel criar diretorio de instalacao"
exit /b 0

:check_write
call :log "Verificando permissao de escrita"
type nul > "%INSTALL_DIR%\.write_test" || call :fail "Sem permissao de escrita no diretorio de instalacao"
del /f /q "%INSTALL_DIR%\.write_test" >nul 2>nul
exit /b 0

:check_disk
call :log "Verificando espaco livre"
powershell -NoProfile -Command "$drive=(Get-Item -LiteralPath '%INSTALL_DIR%').PSDrive.Name; $free=[math]::Floor((Get-PSDrive -Name $drive).Free/1MB); if ($free -lt 512) { exit 1 }" || call :fail "Espaco insuficiente (minimo 512 MB)"
exit /b 0

:validate_hash
if "%REPO_SHA256%"=="" (
	call :log "Hash SHA256 nao informado; validacao ignorada"
	exit /b 0
)
call :log "Validando hash SHA256"
powershell -NoProfile -Command "$actual=(Get-FileHash -Algorithm SHA256 -Path '%TEMP_ZIP%').Hash.ToLower(); if ($actual -ne '%REPO_SHA256%'.ToLower()) { exit 1 }" || call :fail "Hash SHA256 nao confere"
exit /b 0

:copy_config
if "%USERPROFILE%"=="" (
	call :log "USERPROFILE nao definido; pulando copia de config.local.yaml"
	exit /b 0
)
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%" >nul 2>nul
set "CONFIG_PATH=%USER_DATA_DIR%\config.local.yaml"
set "TEMPLATE_PATH=%INSTALL_DIR%\templates\local\config.local.yaml"
if not exist "%CONFIG_PATH%" (
	if exist "%TEMPLATE_PATH%" (
		copy /y "%TEMPLATE_PATH%" "%CONFIG_PATH%" >nul
		call :log "config.local.yaml criado em %CONFIG_PATH%"
	) else (
		call :log "Template de config nao encontrado: %TEMPLATE_PATH%"
	)
) else (
	call :log "config.local.yaml ja existe; mantendo arquivo atual"
)
exit /b 0

:remove_shortcuts
powershell -NoProfile -Command "$desktop=[Environment]::GetFolderPath('Desktop'); if ($desktop) { $p=Join-Path $desktop 'SentinelTray.lnk'; if (Test-Path $p) { Remove-Item -LiteralPath $p -Force } }; $programs=[Environment]::GetFolderPath('Programs'); if ($programs) { $p=Join-Path $programs 'SentinelTray.lnk'; if (Test-Path $p) { Remove-Item -LiteralPath $p -Force } }" >nul 2>nul
if exist "%INSTALL_DIR%\shortcuts\SentinelTray.lnk" del /f /q "%INSTALL_DIR%\shortcuts\SentinelTray.lnk" >nul 2>nul
exit /b 0

:remove_autostart_legacy
powershell -NoProfile -Command "$startup=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\SentinelTray.cmd'; if (Test-Path $startup) { Remove-Item -LiteralPath $startup -Force }; $key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'; if (Test-Path $key) { $props=Get-ItemProperty -Path $key; foreach ($name in $props.PSObject.Properties.Name) { if ($name -in 'PSPath','PSParentPath','PSChildName','PSDrive','PSProvider') { continue }; $value=$props.$name; if ($name -eq 'SentinelTray' -or ($value -is [string] -and $value -match 'run\.py')) { Remove-ItemProperty -Path $key -Name $name -ErrorAction SilentlyContinue } } }" >nul 2>nul
exit /b 0

:rollback
call :log "Rollback: restaurando instalacao anterior"
if not "%BACKUP_DIR%"=="" (
	if exist "%BACKUP_DIR%" (
		if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" >nul 2>nul
		powershell -NoProfile -Command "Move-Item -Path '%BACKUP_DIR%' -Destination '%INSTALL_DIR%'" >nul 2>nul
		exit /b 0
	)
)
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" >nul 2>nul
exit /b 0

:log
echo [%DATE% %TIME%] %*
>>"%LOG_FILE%" echo [%DATE% %TIME%] %*
exit /b 0

:fail
call :log "ERRO: %*"
echo Falha na instalacao. Consulte o log: %LOG_FILE%
exit /b 1