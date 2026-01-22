param(
    [string]$InstallDir = "",
    [string]$ShortcutPath = "",
    [switch]$CreateDesktop,
    [switch]$CreateStartMenu,
    [string]$StartMenuName = "SentinelTray"
)

Set-StrictMode -Version Latest

if (-not $InstallDir) {
    $InstallDir = (Resolve-Path (Join-Path $PSScriptRoot ".."))
}

$target = Join-Path $InstallDir "scripts\run.cmd"
if (-not (Test-Path -LiteralPath $target)) {
    throw "Arquivo de execucao nao encontrado: $target"
}

if (-not $ShortcutPath) {
    $shortcutDir = Join-Path $InstallDir "shortcuts"
    if (-not (Test-Path -LiteralPath $shortcutDir)) {
        New-Item -ItemType Directory -Path $shortcutDir -Force | Out-Null
    }
    $ShortcutPath = Join-Path $shortcutDir "SentinelTray.lnk"
}

$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $InstallDir
$shortcut.WindowStyle = 1
$shortcut.Description = "SentinelTray"
$shortcut.Save()

if ($CreateDesktop) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ($desktop) {
        $desktopShortcut = Join-Path $desktop "SentinelTray.lnk"
        Copy-Item -LiteralPath $ShortcutPath -Destination $desktopShortcut -Force
    }
}

if ($CreateStartMenu) {
    $programs = [Environment]::GetFolderPath("Programs")
    if ($programs) {
        $menuShortcut = Join-Path $programs ("{0}.lnk" -f $StartMenuName)
        Copy-Item -LiteralPath $ShortcutPath -Destination $menuShortcut -Force
    }
}
