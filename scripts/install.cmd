@echo off
setlocal enableextensions enabledelayedexpansion

rem SentinelTray installer (Windows CMD)
rem Licencas: Python (PSF), pip (PSF), GitHub (terms), dependencias via requirements.txt.
rem O usuario deve revisar as licencas antes de instalar.

set "REPO_URL=https://github.com/chrmsantos/sentineltray/archive/refs/heads/master.zip"
set "INSTALL_DIR=%USERPROFILE%\AppData\Local\AxonZ\SentinelTray\SystemData\sentineltray"
set "TEMP_ZIP=%TEMP%\sentineltray.zip"
set "EXTRACT_DIR=%TEMP%\sentineltray-extract"
set "LOG_DIR=%TEMP%\sentineltray-install"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\install_%LOG_TS%.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\install_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

call :log "Iniciando instalacao do SentinelTray"
call :log "Destino: %INSTALL_DIR%"

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%" || call :fail "Nao foi possivel criar diretorio de instalacao"

call :log "Verificando permissao de escrita"
type nul > "%INSTALL_DIR%\.write_test" || call :fail "Sem permissao de escrita no diretorio de instalacao"
del /f /q "%INSTALL_DIR%\.write_test" >nul 2>nul

call :log "Verificando espaco livre"
powershell -NoProfile -Command "$drive=(Get-Item -LiteralPath '%INSTALL_DIR%').PSDrive.Name; $free=[math]::Floor((Get-PSDrive -Name $drive).Free/1MB); if ($free -lt 512) { exit 1 }" || call :fail "Espaco insuficiente (minimo 512 MB)"

call :log "Baixando codigo do GitHub"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%TEMP_ZIP%'" || call :fail "Falha ao baixar o pacote do GitHub"
if not exist "%TEMP_ZIP%" call :fail "Arquivo baixado nao encontrado"

call :log "Extraindo arquivos"
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%" || call :fail "Falha ao preparar diretorio temporario"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%EXTRACT_DIR%' -Force" || call :fail "Falha ao extrair o pacote"

set "SRC_DIR="
for /d %%D in ("%EXTRACT_DIR%\sentineltray-*") do set "SRC_DIR=%%D"
if not defined SRC_DIR call :fail "Diretorio de origem nao encontrado"

call :log "Copiando arquivos do projeto"
powershell -NoProfile -Command "Copy-Item -Path '%SRC_DIR%\*' -Destination '%INSTALL_DIR%' -Recurse -Force" || call :fail "Falha ao copiar arquivos"

cd /d "%INSTALL_DIR%" || call :fail "Falha ao acessar diretorio de instalacao"

call :log "Preparando runtime auto-contido"
call "%INSTALL_DIR%\scripts\bootstrap_self_contained.cmd" || call :fail "Falha ao preparar runtime"

call :log "Limpando arquivos temporarios"
if exist "%TEMP_ZIP%" del /f /q "%TEMP_ZIP%" >nul 2>nul

call :log "Instalacao concluida"
echo Instalacao concluida.
echo Execute: %INSTALL_DIR%\scripts\run.cmd
exit /b 0

:log
echo [%DATE% %TIME%] %*
>>"%LOG_FILE%" echo [%DATE% %TIME%] %*
exit /b 0

:fail
call :log "ERRO: %*"
echo Falha na instalacao. Consulte o log: %LOG_FILE%
exit /b 1