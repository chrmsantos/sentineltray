# SentinelTray 1.0.0-beta.5 Release Notes (2026-01-26)

## Highlights
- Added real-time console status view (1-second counter).
- Added root shortcut for simpler launches.
- Added optional named executable build (SentinelTray.exe) for clearer Task Manager identity.

## Reliability & Safety
- Defensive handling when optional GUI/automation dependencies are missing.
- Clearer status CLI output when status file is missing or unreadable.

## Maintenance
- Removed per-user autostart integration (startup registry entry support and commands).
- Tests now skip optional dependency scenarios when libraries are unavailable.

## Compatibility
- Windows 10/11.
- Python 3.11+ (embedded runtime supported for portable mode).
