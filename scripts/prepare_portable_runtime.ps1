[CmdletBinding()]
param(
    [string]$PythonVersion = "3.11.8",
    [ValidateSet("amd64", "win32")]
    [string]$Architecture = "amd64",
    [string]$RuntimeDir = "runtime\\python",
    [string]$WheelDir = "runtime\\wheels"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    Write-Host "[$Level] $Message"
}

if ($env:OS -notlike "Windows*") {
    Write-Log "ERROR" "Portable runtime prep requires Windows."
    exit 1
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeRoot = Join-Path $root "runtime"
$pythonDir = Join-Path $root $RuntimeDir
$wheelDir = Join-Path $root $WheelDir
$checksumsPath = Join-Path $runtimeRoot "checksums.txt"
$requirements = Join-Path $root "requirements.lock"
$tempRoot = Join-Path $env:TEMP "sentineltray_runtime"
$zipPath = Join-Path $tempRoot "python-embed.zip"

if (-not (Test-Path $requirements)) {
    Write-Log "ERROR" "requirements.lock not found: $requirements"
    exit 1
}

if (-not (Test-Path $tempRoot)) {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
}

$embedUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-$Architecture.zip"
Write-Log "INFO" "Downloading embeddable Python: $embedUrl"
try {
    Invoke-WebRequest -Uri $embedUrl -OutFile $zipPath -UseBasicParsing
} catch {
    Write-Log "ERROR" "Download failed: $($_.Exception.Message)"
    exit 1
}

if (Test-Path $pythonDir) {
    Write-Log "WARN" "Removing existing runtime: $pythonDir"
    Remove-Item -Recurse -Force $pythonDir
}
New-Item -ItemType Directory -Path $pythonDir | Out-Null
Write-Log "INFO" "Extracting runtime to $pythonDir"
Expand-Archive -Path $zipPath -DestinationPath $pythonDir -Force

$pthFile = Get-ChildItem -Path $pythonDir -Filter "*.pth" | Select-Object -First 1
if (-not $pthFile) {
    $pthFile = Get-ChildItem -Path $pythonDir -Filter "*._pth" | Select-Object -First 1
}
if ($pthFile) {
    $pthText = Get-Content -Path $pthFile.FullName -Raw
    if ($pthText -match "#import site") {
        $pthText = $pthText -replace "#import site", "import site"
        Set-Content -Path $pthFile.FullName -Value $pthText -Encoding ASCII
        Write-Log "INFO" "Enabled import site in $($pthFile.Name)"
    } elseif ($pthText -notmatch "import site") {
        Add-Content -Path $pthFile.FullName -Value "`r`nimport site"
        Write-Log "INFO" "Added import site to $($pthFile.Name)"
    }
} else {
    Write-Log "WARN" "No .pth file found; pip may not work as expected."
}

$pythonExe = Join-Path $pythonDir "python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Log "ERROR" "python.exe not found in $pythonDir"
    exit 1
}

Write-Log "INFO" "Ensuring pip is available"
$pipOk = $false
& $pythonExe -m pip --version | Out-Null
if ($LASTEXITCODE -eq 0) {
    $pipOk = $true
}

if (-not $pipOk) {
    $getPip = Join-Path $tempRoot "get-pip.py"
    Write-Log "INFO" "Downloading get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    & $pythonExe $getPip
}

& $pythonExe -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "pip installation failed; portable runtime cannot download wheels."
    exit 1
}

Write-Log "INFO" "Downloading wheels to $wheelDir"
if (-not (Test-Path $wheelDir)) {
    New-Item -ItemType Directory -Path $wheelDir | Out-Null
}
$extraArgs = @()
if ($env:SENTINELTRAY_PIP_INDEX_URL) { $extraArgs += "--index-url"; $extraArgs += $env:SENTINELTRAY_PIP_INDEX_URL }
if ($env:SENTINELTRAY_PIP_TRUSTED_HOST) { $extraArgs += "--trusted-host"; $extraArgs += $env:SENTINELTRAY_PIP_TRUSTED_HOST }
if ($env:SENTINELTRAY_PIP_PROXY) { $extraArgs += "--proxy"; $extraArgs += $env:SENTINELTRAY_PIP_PROXY }
if ($extraArgs.Count -gt 0) { Write-Log "INFO" "Using custom pip settings from environment." }
& $pythonExe -m pip download --only-binary=:all: --dest $wheelDir -r $requirements @extraArgs
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR" "Wheel download failed. Check internet access or proxy settings."
    exit 1
}

Write-Log "INFO" "Removing tray-only wheels (pillow, pystray)"
Get-ChildItem -Path $wheelDir -Filter "pillow-*.whl" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $wheelDir -Filter "pystray-*.whl" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Log "INFO" "Writing checksums to $checksumsPath"
if (-not (Test-Path $runtimeRoot)) {
    New-Item -ItemType Directory -Path $runtimeRoot | Out-Null
}
$files = Get-ChildItem -Path $pythonDir -Recurse -File | Sort-Object FullName
$lines = foreach ($file in $files) {
    $hash = (Get-FileHash -Path $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $relative = $file.FullName.Substring($pythonDir.Length + 1).Replace("\\", "/")
    "$hash  python/$relative"
}
Set-Content -Path $checksumsPath -Value $lines -Encoding UTF8

Write-Log "INFO" "Portable runtime prepared successfully."
