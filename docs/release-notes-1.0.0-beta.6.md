# SentinelTray 1.0.0-beta.6 Release Notes (2026-01-26)

## Highlights
- Improved portability and non-admin operation guarantees.

## Reliability & Safety
- Single-instance mutex now falls back to per-user scope when global mutex is unavailable.
- Defensive handling of optional dependencies remains enforced.

## Documentation
- Added explicit portability and no-admin guidance in README.

## Compatibility
- Windows 10/11.
- Python 3.11+ (embedded runtime supported for portable mode).
