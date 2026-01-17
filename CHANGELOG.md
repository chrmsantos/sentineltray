# Changelog

## 2026-01-16

- Report per-iteration monitoring errors on screen and via WhatsApp.
- Send a startup WhatsApp test message on each run.
- Add periodic healthcheck summaries via WhatsApp.
- Add exponential backoff for consecutive errors.
- Debounce repeated messages within a time window.
- Track error count in tray status.
- Add structured log categories.
- Add local telemetry file for diagnostics.
- Add silent mode for error popup suppression.
- Detect WhatsApp Web login expiration.
- Validate configuration values at startup.

## 2026-01-14

- Initial notifier scaffold with window text detection and WhatsApp senders.
- Update PyYAML dependency to support Python 3.14.
- Fix YAML regex quoting to prevent parse errors.
- Add system tray UI with live status window.
- Update Pillow dependency for Python 3.14 to 12.1.0.
- Update Playwright dependency for Python 3.14.
- Add local override config path for sensitive settings.
- Rename project to SentinelTray.
- Apply GPL-3.0-only license.
- Remove chat_target from public configs.
- Enforce WhatsApp Web as the only supported send mode.
- Auto-create and open local override config when missing or invalid.
- Create per-run detailed logs and retain only the last 5 files.
- Suppress noisy third-party debug logs in per-run files.
- Move local override config to %USERPROFILE%\sentineltray.
- Add local template files with commented guidance.
