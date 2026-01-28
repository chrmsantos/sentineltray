# Maintenance log

## 2026-01-27
- Removed obsolete log artifacts to keep only the five most recent log files per routine.
- Purged generated test and coverage cache artifacts from the repository.
- Fixed portable runtime preparation to install pip correctly before downloading wheels.

## 2026-01-28
- Detector now includes the window title text in scans and treats whitespace-only phrases as empty.
- Window minimization respects allow_window_restore to reduce desktop disruption.
- Added unit tests for phrase handling and regex validation.
