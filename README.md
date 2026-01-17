# SentinelTray

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- Python 3.11+.
- SMTP server access for email delivery.
- Python 3.14 uses PyYAML 6.0.3.

## Setup

1. Create a virtual environment and install dependencies:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Edit config.yaml and set:

- window_title_regex
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- email.smtp_host
- email.from_address
- email.to_addresses
- email.dry_run = false when ready to send

Sensitive settings (like window_title_regex and email credentials) can be stored in a local file:

- %USERPROFILE%\sentineltray\config.local.yaml

This local file overrides config.yaml. You can also set SENTINELTRAY_CONFIG to
point to a local config file.

If config.local.yaml is missing, empty, or invalid, the app creates it,
opens it for editing, and exits so you can fill it.

Local templates are available at templates/local/ with commented instructions
and sample data.

## Run

python main.py

The app runs in the system tray by default. Use the tray menu to open Status.

CLI mode (no tray):

python main.py --cli

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in logs/.
- Third-party debug logs are suppressed to keep logs actionable.
- state.json stores the last sent messages to avoid duplicates.
- Errors detected in each polling iteration are reported on screen and via email.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
- Tray status shows error count and last error reason.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics.
- Silent mode can suppress the error popup while keeping tray status updated.
- Email delivery failures are detected and reported as specific errors.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Sensitive data is always stored under %USERPROFILE%\sentineltray.
