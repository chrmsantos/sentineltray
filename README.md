# SentinelTray

Release candidate: 3.0.0-rc.1 (02-04-2026)

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- SMTP server access for email delivery.

## Setup

Edit config.local.yaml and set:

- monitors (list)
- monitors[].window_title_regex (a unique title prefix is enough)
- monitors[].phrase_regex (empty means any visible text; whitespace-only also means any visible text)
- use single quotes for regex to avoid YAML escape issues
- monitors[].email.smtp_host
- monitors[].email.from_address
- monitors[].email.to_addresses
- monitors[].email.subject
- monitors[].email.retry_attempts
- monitors[].email.retry_backoff_seconds
- monitors[].email.dry_run = true on first run; set false after validation
- monitors[].email.smtp_username (no config local)
- monitors[].email.smtp_password is always prompted at startup when a username is configured (per monitor)
- allow_window_restore, send_repeated_matches
- log_only_mode
- log_level, log_console_level, log_console_enabled
- log_max_bytes, log_backup_count, log_run_files_keep
- min_repeat_seconds, error_notification_cooldown_seconds
- window_error_backoff_base_seconds, window_error_backoff_max_seconds
- window_error_circuit_threshold, window_error_circuit_seconds
- email_queue_file, email_queue_max_items, email_queue_max_age_seconds
- email_queue_max_attempts, email_queue_retry_base_seconds
- config_version (optional, default 1)

The application always reads the local config file. Default location is driven by
`SENTINELTRAY_DATA_DIR` when set. Otherwise it falls back to:

- %LOCALAPPDATA%\Axon\SentinelTray\config\config.local.yaml

If config.local.yaml is missing or invalid, the app opens the console error view with guidance.

Local documentation for sample state files lives under templates/local/.

## Run

scripts\run.cmd

When a venv is present, the launcher uses it automatically.

Manual venv activation from CMD:

scripts\activate_venv.cmd

If you run main.py directly, it automatically adds src/ to the import path.
SentinelTray starts in the foreground console interface. Use the menu to open Config,
trigger a manual scan, or Exit.

For a simple start, use the shortcut at the project root: Executar SentinelTray.cmd.

## Named executable (no admin)

To make the process clearly identifiable in Task Manager as SentinelTray.exe, build a named
executable locally (no admin privileges required):

scripts\build_named_exe.cmd

This creates dist\SentinelTray.exe. Launch it normally; in Task Manager it will appear as
SentinelTray.exe instead of python.exe/pythonw.exe.

## Config editing

Use the console menu Config option to edit settings. It opens a temporary file, validates
it, and writes it back to config.local.yaml on save.

## Regex (wildcards) and examples

Use regex in window title/name strings and in the text to look for. Tips:

- `.*` matches any sequence of characters.
- `.` matches a single character.
- `?` makes the previous character optional.
- `[A-Z]` matches a set/range.
- `\d` for digits, `\s` for spaces, `^` start and `$` end.

Examples:

- window_title_regex: 'Aplicacao.*Desktop'
- window_title_regex: '^App\\.Monitor\\..*'
- phrase_regex: 'PROTOCOLS?\\s+NOT\\s+RECEIVED'
- phrase_regex: 'ALERT|CRITICAL'

## Monitors (title + text + email)

Use `monitors` for all monitoring entries.
Each item must include its own email configuration.

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

- Logs are written per execution with detailed fields and kept with a max of 3 files in %SENTINELTRAY_DATA_DIR%\logs (values above 3 are capped).
- Logs rotate by size using log_max_bytes and log_backup_count.
- JSON logs are written alongside text logs in sentineltray.jsonl and per-run sentineltray_*.jsonl.
- If the config is missing or invalid, SentinelTray still starts in "Config Error" mode and exposes the error details in the console.
- When another instance is already running, a notice is shown and the new launch exits cleanly.
- Script logs (install/run/bootstrap) are stored under %SENTINELTRAY_DATA_DIR%\logs\scripts.
- On startup, SentinelTray reconciles config.local.yaml with the official template and creates the local config from the template if missing.
- Third-party debug logs are suppressed to keep logs actionable.
- Logs and telemetry redact sensitive strings (emails and local paths) and store match summaries as hashes.
- Runtime artifacts are integrity-checked via runtime/checksums.txt.
- state.json stores the last sent messages to avoid duplicates.
- Errors detected in each polling iteration are reported via email immediately.
- When the target window is unavailable or disabled, an alert is sent and the scan is skipped.
- Monitor failures use a per-monitor circuit breaker and local backoff to avoid alert storms.
- Email delivery failures are queued locally and retried with exponential backoff.
- Error notifications are rate-limited via error_notification_cooldown_seconds.
- Startup test and periodic healthchecks update status/logs but do not send email.
- When the target window is open, scans restore (if minimized), then ensure it is foreground and maximized before reading text.
- Phrase matching ignores accents, is case-insensitive, and matches partial text occurrences.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Messages identical to the immediately previous scan are skipped.
- Messages with a lower leading number than the previous scan are skipped.
- send_repeated_matches still respects min_repeat_seconds if configured.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics and lives in %SENTINELTRAY_DATA_DIR%\logs.
- Log-only mode skips normal alert sends but still emails error notifications.
- Email delivery failures are detected and reported as specific errors.
- Match alert emails use subject "SentinelTray Match Alert"; error alerts use "SentinelTray Error Alert".
- Info-category emails are suppressed; subjects like "SentinelTray Info" are never sent.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Scans run only after 2+ minutes of user inactivity.
- Sensitive data is always stored under %SENTINELTRAY_DATA_DIR%; operational logs stay in %SENTINELTRAY_DATA_DIR%\logs.
- Privacy policy in PRIVACY.md.
- Security policy in SECURITY.md.
- Licenses and third parties in docs/licenses.md.
- Releases include provenance (SLSA).
