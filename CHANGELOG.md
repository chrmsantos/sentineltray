# Changelog

## 2026-01-16

- Report per-iteration monitoring errors on screen and via email.
- Send a startup email test message on each run.
- Add periodic healthcheck summaries via email.
- Add exponential backoff for consecutive errors.
- Debounce repeated messages within a time window.
- Track error count in tray status.
- Add structured log categories.
- Add local telemetry file for diagnostics.
- Add silent mode for error popup suppression.
- Detect email delivery failures.
- Replace WhatsApp delivery with SMTP email.
- Validate configuration values at startup.
- Add watchdog for long scan stalls.
- Auto-create local override config on startup when missing.
- Enforce sensitive data paths under user local sentineltray folder.
- Add privacy policy and tests for LGPD compliance.
- Add config error prompt with edit or exit option.
- Open status on left-click and refresh tray UI in PT-BR.
- Add Gmail SMTP example to local template.
- Add single-instance guard and installer script.
- Add email subject, retries, regex validation, and status export.
- Use eye icon and auto-open status window on startup.

## 2026-01-14

- Initial notifier scaffold with window text detection and email senders.
- Update PyYAML dependency to support Python 3.14.
- Fix YAML regex quoting to prevent parse errors.
- Add system tray UI with live status window.
- Update Pillow dependency for Python 3.14 to 12.1.0.
- Remove Playwright dependency after switching to email.
- Add local override config path for sensitive settings.
- Rename project to SentinelTray.
- Apply GPL-3.0-only license.
- Remove chat_target from public configs.
- Enforce email as the only supported send mode.
- Auto-create and open local override config when missing or invalid.
- Create per-run detailed logs and retain only the last 5 files.
- Suppress noisy third-party debug logs in per-run files.
- Move local override config to %USERPROFILE%\sentineltray.
- Add local template files with commented guidance.
