# SentinelTray 1.0.0-beta.3 (2026-01-23)

## Highlights

- Tray-only configuration editing with automatic re-encryption.
- Config folder rename (UserData → config) across defaults and docs.
- Per-user startup registration via scripts/run.cmd.

## Changes

- Add tray config editor with auto-encryption after editing.
- Remove CLI and expose only Config/Exit from the tray icon.
- Rename UserData folder to config across defaults and docs.
- Add per-user startup registration commands in scripts/run.cmd.

## Notes

- Config is stored under %SENTINELTRAY_DATA_DIR%\config.local.yaml.enc.
- Use the tray menu Config option to edit settings.
