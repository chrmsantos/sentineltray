# SentinelTray 1.0.0-beta.10 Release Notes (2026-02-03)

## Highlights

- Security: SMTP password must be provided via SENTINELTRAY_SMTP_PASSWORD; config secrets are rejected.
- Logging: retention capped at 3 files; scan_id added to logs; info logs are deduplicated.
- Scanning: window lookup now retries; minimized windows are restored and maximized before scanning.
- Console: status header shows EXECUTANDO/PARADO, ERROS count, last message timestamp, and email queue status.

## Detailed changes

- Notifications: suppressed info-category email subjects to avoid “SentinelTray Info”.
- Configuration: defaults are applied with warnings for missing optional keys.
- First run safety: requires dry_run=true unless log-only mode is enabled.
- Telemetry/status: email queue stats propagated to status snapshots.

## Upgrade notes

- Set SENTINELTRAY_SMTP_PASSWORD (and optionally SENTINELTRAY_SMTP_USERNAME) in the environment.
- For first execution, keep email.dry_run=true, validate, then switch to false.
- Log retention is capped to 3 files per routine.
