# Changelog

## 2026-02-03

- Notifications: drop info-category emails to avoid "SentinelTray Info" subjects.
- Scanning: when the target window is open, restore if minimized, then enforce foreground and maximized before scanning.
- Console: status header now shows EXECUTANDO/PARADO, error count, and last message sent indicator.
- Console: display includes ERROS count and última mensagem line in the status header.

## 2026-02-02

- Notifications: suppressed non-alert informational emails (startup test, healthcheck); only match and error emails are sent.

## 2026-01-28 (beta.9)

- Performance: cached compiled phrase regex and reduced logging overhead.
- Cleanup: removed WhatsApp artifacts from logs and coverage outputs.
- Maintenance: Markdown lint fixes and test updates for monitor-only schema.

## 2026-01-28

- Config editor now reconciles against the official template (comment-preserving) and adds a manual reconcile command with dry-run.
- Added audit hashes for template sync and retention for config error logs.
- Updated local data paths to Axon branding and refreshed docs.
- Tightened config typing and validation checks.
