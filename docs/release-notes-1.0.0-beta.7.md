# SentinelTray 1.0.0-beta.7 Release Notes (2026-01-27)

## Highlights
- Console UI replaces tray icon; runs in the foreground with menu commands.
- Graceful shutdown on window close or Ctrl+C.

## Reliability & Safety
- Config errors now show a console error view with guidance.
- Console watch loop handles interruptions cleanly.

## Maintenance
- Removed tray-only dependencies from requirements.
- Portable runtime prep drops tray-only wheels.

## Compatibility
- Windows 10/11.
- Python 3.11+ (embedded runtime supported for portable mode).
