[CmdletBinding()]
param(
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    Write-Host "[$Level] $Message"
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$destRoot = Join-Path $root $OutputDir
$packageDir = Join-Path $destRoot "sentineltray_portable_$timestamp"
$zipPath = Join-Path $destRoot "sentineltray_portable_$timestamp.zip"

if (-not (Test-Path $destRoot)) {
    New-Item -ItemType Directory -Path $destRoot | Out-Null
}

Write-Log "INFO" "Creating package at $packageDir"
New-Item -ItemType Directory -Path $packageDir | Out-Null

$include = @(
    "assets",
    "scripts",
    "src",
    "templates",
    "main.py",
    "cli.py",
    "README.md",
    "LICENSE",
    "PRIVACY.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "requirements.lock",
    "runtime"
)

foreach ($item in $include) {
    $source = Join-Path $root $item
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $packageDir $item) -Recurse -Force
    }
}

$configDir = Join-Path $packageDir "config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

$templateConfig = Join-Path $root "templates\local\config.local.yaml"
if (Test-Path $templateConfig) {
    Copy-Item -Path $templateConfig -Destination (Join-Path $configDir "config.local.yaml") -Force
}

Write-Log "INFO" "Creating zip archive"
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -Force

Write-Log "INFO" "Portable package ready: $zipPath"
