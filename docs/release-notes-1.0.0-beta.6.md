# SentinelTray 1.0.0-beta.6 Release Notes (2026-01-26)

## Highlights

- Improved portability and non-admin operation guarantees.

## Reliability & Safety

- Single-instance mutex now falls back to per-user scope when global mutex is unavailable.
- Defensive handling of optional dependencies remains enforced.
- Tray icon now runs on the Windows main message loop to avoid missing tray registration.
- Configuration failures now open a "Config Error" tray mode with guidance instead of exiting.
- Launch attempts while already running now show a user notice and exit cleanly.

## Documentation

- Added explicit portability and no-admin guidance in README.

## Compatibility

- Windows 10/11.
- Python 3.11+ (embedded runtime supported for portable mode).
