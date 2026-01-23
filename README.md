# SentinelTray

Beta version: 1.0.0-beta.3 (01-23-2026)

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- SMTP server access for email delivery.

## Setup

Edit config.local.yaml and set:

- window_title_regex (a unique title prefix is enough)
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- email.smtp_host
- email.from_address
- email.to_addresses
- email.subject
- email.retry_attempts
- email.retry_backoff_seconds
- email.dry_run = false when ready to send
- status_export_csv, allow_window_restore, send_repeated_matches
- log_only_mode, config_checksum_file, min_free_disk_mb
- log_level, log_console_level, log_console_enabled
- log_max_bytes, log_backup_count, log_run_files_keep
- min_repeat_seconds, error_notification_cooldown_seconds
- window_error_backoff_base_seconds, window_error_backoff_max_seconds
- window_error_circuit_threshold, window_error_circuit_seconds
- email_queue_file, email_queue_max_items, email_queue_max_age_seconds
- email_queue_max_attempts, email_queue_retry_base_seconds
- log_throttle_seconds
- config_version (optional, default 1)

The application always reads the local config file. Default location is driven by
`SENTINELTRAY_DATA_DIR` when set. Otherwise it falls back to:

- %LOCALAPPDATA%\AxonZ\SentinelTray\config\config.local.yaml

If config.local.yaml is missing or invalid, the app exits with guidance.

Local documentation for sample state files lives under templates/local/.

## Run

scripts\run.cmd

Foreground (with console output):

scripts\run.cmd /foreground

Background (explicit):

scripts\run.cmd /background

## Startup (per-user)

Install on login:

scripts\run.cmd /install-startup

Remove from login:

scripts\run.cmd /remove-startup

Check status:

scripts\run.cmd /startup-status

If you run main.py directly, it automatically adds src/ to the import path.
SentinelTray starts in the background with a green tray icon. Left-click or right-click shows
Config and Exit.

## Config editing

Use the tray menu Config option to edit settings. It decrypts in memory, opens a temporary file
for editing, validates it, and re-encrypts on save.

## Config protection

When config.local.yaml.enc is present, SentinelTray loads it automatically.
If only config.local.yaml exists, SentinelTray attempts to encrypt it on startup.

## Regex (wildcards) and examples

Use regex in window title/name strings and in the text to look for. Tips:

- `.*` matches any sequence of characters.
- `.` matches a single character.
- `?` makes the previous character optional.
- `[A-Z]` matches a set/range.
- `\d` for digits, `\s` for spaces, `^` start and `$` end.

Examples:

- window_title_regex: 'Siscam.*Desktop'
- window_title_regex: '^Sino\\.Siscam\\..*'
- phrase_regex: 'PROTOCOLS?\\s+NOT\\s+RECEIVED'
- phrase_regex: 'ALERT|CRITICAL'

## Multiple monitors (title + text + email)

To monitor more than one title + text pair, use `monitors`.
Each item must include its own email configuration.
When `monitors` is used, the top-level `email` block can be omitted.

Exemplo:

```yaml
monitors:
   - window_title_regex: 'APP1'
      phrase_regex: 'ALERT1'
      email:
         smtp_host: 'smtp.local'
         smtp_port: 587
         smtp_username: ''
         smtp_password: ''
         from_address: 'alerts1@example.com'
         to_addresses: ['ops1@example.com']
         use_tls: true
         timeout_seconds: 10
         subject: 'SentinelTray Notification'
         retry_attempts: 0
         retry_backoff_seconds: 0
         dry_run: true
   - window_title_regex: 'APP2'
      phrase_regex: 'ALERT2'
      email:
         smtp_host: 'smtp.local'
         smtp_port: 587
         smtp_username: ''
         smtp_password: ''
         from_address: 'alerts2@example.com'
         to_addresses: ['ops2@example.com']
         use_tls: true
         timeout_seconds: 10
         subject: 'SentinelTray Notification'
         retry_attempts: 0
         retry_backoff_seconds: 0
         dry_run: true
```

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in %SENTINELTRAY_DATA_DIR%\logs (values above 5 are capped).
- Logs rotate by size using log_max_bytes and log_backup_count.
- JSON logs are written alongside text logs in sentineltray.jsonl and per-run sentineltray_*.jsonl.
- Script logs (install/run/bootstrap) are stored under %SENTINELTRAY_DATA_DIR%\logs\scripts.
- Third-party debug logs are suppressed to keep logs actionable.
- Logs, telemetry, and status exports redact sensitive strings (emails and local paths) and store match summaries as hashes.
- Runtime artifacts are integrity-checked via runtime/checksums.txt.
- state.json stores the last sent messages to avoid duplicates.
- Errors detected in each polling iteration are reported via email immediately.
- When the target window is unavailable or disabled, an alert is sent and the scan is skipped.
- Monitor failures use a per-monitor circuit breaker and local backoff to avoid alert storms.
- Email delivery failures are queued locally and retried with exponential backoff.
- Error notifications are rate-limited via error_notification_cooldown_seconds.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Minimized windows are restored to read text.
- Phrase matching ignores accents, is case-insensitive, and matches partial text occurrences.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- send_repeated_matches still respects min_repeat_seconds if configured.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics and lives in %SENTINELTRAY_DATA_DIR%\logs.
- Status export JSON available at status_export_file (config\logs by default).
- Status export CSV available at status_export_csv (config\logs by default).
- Log-only mode skips normal alert sends but still emails error notifications.
- Email delivery failures are detected and reported as specific errors.
- Email subject always includes SentinelTray, and the body starts with a SentinelTray title in English.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Scans run only after 2+ minutes of user inactivity.
- Sensitive data is always stored under %SENTINELTRAY_DATA_DIR%; operational logs stay in %SENTINELTRAY_DATA_DIR%\logs.
- Privacy policy in PRIVACY.md.
- Security policy in SECURITY.md.
- Licenses and third parties in docs/licenses.md.
- Releases include provenance (SLSA).
