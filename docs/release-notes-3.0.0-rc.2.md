# Release notes — 3.0.0-rc.2 (2026-02-05)

## Highlights

- Window title matching now supports partial titles using regex search.
- Console action [W] lists matching window titles per monitor for quick validation.
- Console header shows last scan timestamp and last error for faster troubleshooting.
- SMTP auth failures now prompt for updated credentials without restart.

## Notes

- Use ^...$ anchors in window_title_regex if you need exact matches.
