# Architecture

## Overview

- Window text detection uses UI Automation via pywinauto.
- Email delivery uses SMTP with optional TLS.
- State is stored in state.json to prevent duplicate sends.
- Logs are created per execution with detailed fields and kept with a max of 5 files.
- Third-party debug log noise is suppressed at the logger level.
- System tray UI shows status and controls exit.
- Errors in each polling iteration are reported on screen and via email.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Tray icon is rendered via Pillow with fixed-size rectangle glyphs.
- Tray status shows error count and last error reason.
- Logs include a structured category field (scan/send/error/etc).
- Local telemetry file captures last activity for quick diagnostics.
- Silent mode can suppress the error popup while keeping tray status updated.
- Email delivery failures are detected and reported as specific errors.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Sensitive data paths are enforced under %USERPROFILE%\sentineltray.
- Local override config can be loaded from %USERPROFILE%\sentineltray\config.local.yaml.
- Missing, empty, or invalid local override triggers file creation and edit prompt.
- Local file templates live under templates/local/.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.
