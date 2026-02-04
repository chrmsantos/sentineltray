# Release notes — 3.0.0-rc.1 (2026-02-04)

## Highlights

- Startup integrity checks for data/log directories and portable runtime markers.
- Automatic reconciliation between the official config template and local config.
- SMTP username is now configured only in config.local.yaml; SMTP password is prompted at startup.

## Breaking changes

- SMTP password in config is ignored; provide it at startup or via SENTINELTRAY_SMTP_PASSWORD/_N.

## Notes

- Portable mode remains supported; keep runtime and config inside the project folder for plug-and-play.
