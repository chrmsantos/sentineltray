@echo off
setlocal enableextensions enabledelayedexpansion

rem SentinelTray installer (Windows CMD)
rem Licencas: Python (PSF), pip (PSF), GitHub (terms), dependencias via requirements.txt.
rem O usuario deve revisar as licencas antes de instalar.

set "REPO_URL=https://github.com/chrmsantos/sentineltray/archive/refs/heads/master.zip"
set "INSTALL_DIR=%USERPROFILE%\sentineltray-app"
set "TEMP_ZIP=%TEMP%\sentineltray.zip"
set "EXTRACT_DIR=%TEMP%\sentineltray-extract"

echo Instalando SentinelTray em "%INSTALL_DIR%"...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Baixando codigo do GitHub...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%TEMP_ZIP%'" || goto :error

echo Extraindo arquivos...
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%EXTRACT_DIR%' -Force" || goto :error

for /d %%D in ("%EXTRACT_DIR%\sentineltray-*") do set "SRC_DIR=%%D"
if not defined SRC_DIR goto :error

echo Copiando arquivos do projeto...
powershell -NoProfile -Command "Copy-Item -Path '%SRC_DIR%\*' -Destination '%INSTALL_DIR%' -Recurse -Force" || goto :error

echo Verificando Python...
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instalando via winget...
  winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements || goto :error
)

cd /d "%INSTALL_DIR%"

echo Criando ambiente virtual...
python -m venv .venv || goto :error

echo Instalando dependencias...
call .venv\Scripts\activate || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements.txt || goto :error

echo Instalacao concluida.
echo Execute: %INSTALL_DIR%\ .venv\Scripts\python.exe main.py
exit /b 0

:error
echo Falha na instalacao.
exit /b 1