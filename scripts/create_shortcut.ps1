param(
    [string]$InstallDir = "",
    [string]$ShortcutPath = "",
    [switch]$CreateDesktop,
    [switch]$CreateStartMenu,
    [string]$StartMenuName = "SentinelTray",
    [string]$LogPath = ""
)

Set-StrictMode -Version Latest

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[{0}] [{1}] {2}" -f $timestamp, $Level.ToUpperInvariant(), $Message
    Write-Host $line
    if ($LogPath) {
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
}

try {
    Write-Log "Iniciando criacao de atalhos"

    if (-not $InstallDir) {
        $InstallDir = (Resolve-Path (Join-Path $PSScriptRoot ".."))
    }

    $target = Join-Path $InstallDir "scripts\run.cmd"
    Write-Log "InstallDir: $InstallDir"
    Write-Log "Target: $target"

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

    Write-Log "ShortcutPath: $ShortcutPath"

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
            Write-Log "Atalho criado no Desktop: $desktopShortcut"
        }
    }

    if ($CreateStartMenu) {
        $programs = [Environment]::GetFolderPath("Programs")
        if ($programs) {
            $menuShortcut = Join-Path $programs ("{0}.lnk" -f $StartMenuName)
            Copy-Item -LiteralPath $ShortcutPath -Destination $menuShortcut -Force
            Write-Log "Atalho criado no Menu Iniciar: $menuShortcut"
        }
    }

    Write-Log "Atalhos criados com sucesso"
}
catch {
    Write-Log "Falha ao criar atalhos: $($_.Exception.Message)" "ERROR"
    throw
}
