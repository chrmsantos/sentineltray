# SentinelTray

Versão beta: 0.2.0-beta.1 (19-01-2026)

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- Python 3.11+.
- SMTP server access for email delivery.
- Python 3.14 uses PyYAML 6.0.3.

## Setup

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Edit config.yaml and set:

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
- status_export_csv, status_refresh_seconds, allow_window_restore, start_minimized
- log_only_mode, config_checksum_file, min_free_disk_mb
- log_level, log_console_level, log_console_enabled
- log_max_bytes, log_backup_count, log_run_files_keep

Sensitive settings (like window_title_regex and email credentials) can be stored in a local file:

- %USERPROFILE%\.stray_local\config.local.yaml

This local file overrides config.yaml. You can also set SENTINELTRAY_CONFIG to
point to a local config file.

If config.local.yaml is missing, empty, or invalid, the app creates it,
opens it for editing, and exits so you can fill it.

Local templates are available at templates/local/ with commented instructions
and sample data.

## Instalacao automatica (Windows CMD)

Use o script em scripts/install.cmd para baixar o projeto do GitHub e instalar
Python, dependencias e o ambiente virtual.
O instalador gera logs em %TEMP%\sentineltray-install e mantém apenas os 5 mais recentes.

## Run

python main.py

The app runs in the system tray by default. Use the tray menu to open Status.
Clique com o botão esquerdo no ícone para abrir o Status. A janela abre automaticamente ao iniciar, a menos que start_minimized esteja ativo.
No Status, use os botões para abrir o arquivo de configurações, a pasta de dados, os logs e o repositório, além de copiar e atualizar o status.
O título da interface mostra o nome e a descrição do projeto.

CLI mode (no tray):

```powershell
python main.py --cli
```

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in logs/ (values above 5 are capped).
- Logs rotate by size using log_max_bytes and log_backup_count.
- Third-party debug logs are suppressed to keep logs actionable.
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
- Tray status shows error count and last error reason.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics.
- Status export JSON available at status_export_file.
- Status export CSV available at status_export_csv.
- UI refresh interval is configurable via status_refresh_seconds.
- Data folder shortcut available in the Status window.
- Status window uses larger, user-friendly text, fits its content, and shows version/date discreetly.
- Silent mode can suppress the error popup while keeping tray status updated.
- Log-only mode skips normal alert sends but still emails error notifications.
- Email delivery failures are detected and reported as specific errors.
- Email subject always includes SentinelTray, and the body starts with a SentinelTray title in PT-BR.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Scans run only after 2+ minutes of user inactivity.
- Sensitive data is always stored under %USERPROFILE%\.stray_local.
- Política de privacidade em PRIVACY.md.
