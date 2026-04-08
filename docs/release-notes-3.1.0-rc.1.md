# Release notes — 3.1.0-rc.1 (2026-04-08)

## Highlights

- Automatic scan pause while the user is active: scans are skipped when the system idle time is below the configured threshold, reducing interference during active use.
- Two new config options control the behaviour: `pause_on_user_active` and `pause_idle_threshold_seconds`.
- Manual scans (triggered via the console) always execute regardless of user activity.

## New config options

| Option | Default | Description |
|---|---|---|
| `pause_on_user_active` | `true` | Skip automatic scans while user is active. |
| `pause_idle_threshold_seconds` | `180` | Seconds of idle time required before scanning resumes. |

## Notes

- Existing configs without these keys will use the defaults above (no action required).
- Status display shows `PAUSADO (usuário ativo)` when a scan is skipped.
