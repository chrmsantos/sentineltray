# SentinelTray

Versão beta: 0.2.0-beta.1 (19-01-2026)

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- SMTP server access for email delivery.

## Setup (self-contained)

1. Bootstrap the bundled runtime:

   ```powershell
   scripts\bootstrap_self_contained.cmd
   ```

   This downloads embedded CPython, pip, and all wheels into runtime/ using requirements.lock.
   Checksums are stored in runtime/checksums.txt and validated on startup.

2. Edit config.local.yaml and set:

- window_title_regex (prefixo unico do titulo e suficiente)
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- email.smtp_host
- email.from_address
- email.to_addresses
- email.subject
- email.retry_attempts
- email.retry_backoff_seconds
- email.dry_run = false when ready to send
- status_export_csv, status_refresh_seconds, allow_window_restore, start_minimized, auto_start, send_repeated_matches
- log_only_mode, config_checksum_file, min_free_disk_mb
- log_level, log_console_level, log_console_enabled
- log_max_bytes, log_backup_count, log_run_files_keep

The application always reads the local config file:

- %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\config.local.yaml

If config.local.yaml is missing, empty, or invalid, the app creates it,
opens it for editing, and exits so you can fill it.

Local documentation for sample state files lives under templates/local/.

## Instalacao automatica (Windows CMD)

Use o script em scripts/install.cmd para baixar o projeto do GitHub e instalar
o runtime auto-contido (CPython embutido + dependencias).
O instalador gera logs em %TEMP%\sentineltray-install e mantém apenas os 5 mais recentes.

## Run

scripts\run.cmd

If you run main.py directly, it automatically adds src/ to the import path.

SentinelTray inicia em segundo plano com um ícone na bandeja do sistema.
Clique com o botão esquerdo para abrir o CLI e usar os comandos.
Clique com o botão direito para Abrir ou Sair.

Comandos principais:

- status
- pause / resume / toggle
- watch [segundos]
- open config | open data | open logs | open repo
- help
- exit

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\logs (values above 5 are capped).
- Logs rotate by size using log_max_bytes and log_backup_count.
- Third-party debug logs are suppressed to keep logs actionable.
- Logs, telemetry, and status exports redact sensitive strings (emails and local paths) and store match summaries as hashes.
- Runtime artifacts are integrity-checked via runtime/checksums.txt.
- state.json stores the last sent messages to avoid duplicates.
- Errors detected in each polling iteration are reported on screen and via email immediately.
- When the target window is unavailable or disabled, an alert is sent and the scan is skipped.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Janelas minimizadas sao restauradas para leitura do texto.
- Phrase matching ignores accents, is case-insensitive, and matches partial text occurrences.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics and lives in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\logs.
- Status export JSON available at status_export_file (UserData\logs by default).
- Status export CSV available at status_export_csv (UserData\logs by default).
- Log-only mode skips normal alert sends but still emails error notifications.
- Email delivery failures are detected and reported as specific errors.
- Email subject always includes SentinelTray, and the body starts with a SentinelTray title in PT-BR.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Scans run only after 2+ minutes of user inactivity.
- Sensitive data is always stored under %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData; operational logs stay in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\logs.
- Política de privacidade em PRIVACY.md.
