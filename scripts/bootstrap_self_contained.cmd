@echo off
setlocal enableextensions enabledelayedexpansion

rem Bootstrap self-contained runtime (embedded CPython + offline wheels)

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "RUNTIME_DIR=%ROOT%\runtime"
set "PY_DIR=%RUNTIME_DIR%\python"
set "CHECKSUM_FILE=%RUNTIME_DIR%\checksums.txt"

set "LOG_DIR=%TEMP%\sentineltray-install"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "LOG_TS=%%I"
set "LOG_FILE=%LOG_DIR%\bootstrap_%LOG_TS%.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
powershell -NoProfile -Command "Get-ChildItem -Path '%LOG_DIR%\bootstrap_*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Force -ErrorAction SilentlyContinue" >nul 2>nul

if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%" || exit /b 1

if not exist "%CHECKSUM_FILE%" (
	call :log "Checksum ausente; runtime incompleto"
	exit /b 1
)

call :log "Validando checksums do runtime"
powershell -NoProfile -Command "$root='%RUNTIME_DIR%'; $ok=$true; Get-Content '%CHECKSUM_FILE%' | ForEach-Object { if ($_ -match '^(.*)\|(.*)$') { $path = Join-Path $root $Matches[1]; $hash=$Matches[2]; if (-not (Test-Path $path)) { $ok=$false } else { $actual=(Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLower(); if ($actual -ne $hash) { $ok=$false } } } }; if (-not $ok) { exit 1 }" || (
	call :log "Checksum invalido; runtime corrompido"
	exit /b 1
)

if not exist "%PY_DIR%\python.exe" (
	call :log "Runtime ausente; python.exe nao encontrado"
	exit /b 1
)

call :log "Runtime validado"
exit /b 0

:log
echo [%DATE% %TIME%] %*
>>"%LOG_FILE%" echo [%DATE% %TIME%] %*
exit /b 0
