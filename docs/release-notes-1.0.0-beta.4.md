# Release Notes - 1.0.0-beta.4 (2026-01-23)

## Highlights

- Portable runtime setup and packaging are now automated.
- Alerts are safer: immediate duplicate scans and decreasing numeric prefixes are suppressed.
- Email subjects are standardized for match and error alerts.

## Changes

- Portable mode: automatic runtime preparation, wheel bootstrap, proxy-aware downloads, and packaging scripts.
- Startup logging now records portable mode, encryption method, and SMTP healthcheck warnings.
- Tray UX: exit confirmation removed; tooltip reflects status.
- Config template updated with clear, per-item comments.
- Subject lines fixed to "SentinelTray Match Alert" and "SentinelTray Error Alert".

## Notes

- Windows-only runtime remains required.
- Initial bootstrap may download Python/wheels if missing (internet required).
