# Changelog

## Unreleased

- Improve visibility timeout handling to reduce false warnings when the target window reports visible/enabled after retries.
- Stabilize scan preparation by refocusing and clicking the title bar to reduce interference from temporary overlays.
- Fix installer shortcut creation when create_shortcut.ps1 is missing after copy.
- Fail fast when the downloaded package lacks the runtime bundle.
- Ensure installer stops after fatal errors instead of continuing to later steps.
- Add WhatsApp Desktop delivery channel with dedicated configuration and UI controls.
- Add manual scan, update/restart options, and startup validation of monitored window and WhatsApp availability.
- Add automated security checks (CodeQL, pip-audit, bandit), SBOM, and SLSA provenance for releases.
- Add security and audit documentation, plus issue/PR templates and release checklist.
- Add mypy type checking configuration and CI step.

## 2026-01-21 (1.0.0-beta.1)

- Use atomic writes for telemetry, status exports, state storage, and config checksums to prevent corruption on abrupt shutdown.
- Restore CLI entrypoint module to resolve missing import at startup.
- Update status panel wording to include monitored window/text and next scan time.
- Add write failure counters to exports and improve runtime preflight checks.
- Make window visibility checks more tolerant to avoid false unavailable errors.
- Adjust alert email wording for detected text.
- Stop auto-creating config templates; report configuration errors with explicit guidance and exit.
- Start hidden with tray icon for CLI access and background operation.
- Add multi-monitor support with per-monitor email settings and regex usage guidance.

## 2026-01-20 (0.2.0-beta.7)

- Move sensitive user data and operational logs/status to %SENTINELTRAY_DATA_DIR% (portable) with fallback to %LOCALAPPDATA%\AxonZ\SentinelTray\UserData.
- Redact sensitive data from logs, status exports, and telemetry while preserving diagnostic utility.
- Add status report emails every 7 scan iterations and surface last_report_send in exports/UI.
- Set default scan interval to 3 minutes in templates.
- Add self-contained runtime bootstrap with locked dependencies and offline wheelhouse.
- Show the UI by default on first initialization (start_minimized disabled in templates).
- Add runtime checksum validation, stricter log path validation, and Windows mutex for single-instance stability.
- Improve window detection retries and expand log redaction for tokens/phones.
- Load configuration exclusively from config.local.yaml and reject overrides.

## 2026-01-19 (0.2.0-beta.6)

- Store operational logs, telemetry, and status exports under the project logs/ folder; sensitive data remains in %SENTINELTRAY_DATA_DIR%.
- Allow running main.py directly by bootstrapping src/ onto the import path.

## 2026-01-19 (0.2.0-beta.5)

- Disable email sending for the session after SMTP authentication failure to prevent repeated retries.
- Resolve ambiguous window matches by selecting the most visible/focused candidate.

## 2026-01-19 (0.2.0-beta.4)

- Send user alerts when the target window is unavailable and skip that scan.

## 2026-01-19 (0.2.0-beta.3)

- Harden Windows installer with structured logging, retention, and stricter error handling.
- Ensure error notifications always attempt immediate email delivery.

## 2026-01-19 (0.2.0-beta.2)

- Move local user data directory to %SENTINELTRAY_DATA_DIR% (portable) for configs, logs, and telemetry.
- Skip scans without error alerts when the target window is unavailable or disabled.

## 2026-01-19 (0.2.0-beta.1)

- Enforce log retention caps at 5 files, clamping higher configured values.
- Add pause/resume and exit controls in the status UI with a Commands menu and larger layout.
- Unify all status commands in the Commands menu and remove redundant buttons.
- Increase UI text size and rewrite labels in user-friendly language.
- Fit UI windows to content and standardize timestamp display format in the status panel.
- Gate scans to run only after 2+ minutes of user inactivity.
- Ensure email subjects always include SentinelTray and bodies use friendly PT-BR text.
- Make phrase matching accent-insensitive with partial text detection.
- Display version/date discreetly in the status UI.
- Make phrase matching case-insensitive.

## 2026-01-16

- Report per-iteration monitoring errors on screen and via email.
- Send a startup email test message on each run.
- Add periodic healthcheck summaries via email.
- Add exponential backoff for consecutive errors.
- Debounce repeated messages within a time window.
- Track error count in tray status.
- Add structured log categories.
- Add local telemetry file for diagnostics.
- Add silent mode for error popup suppression.
- Detect email delivery failures.
- Replace WhatsApp delivery with SMTP email.
- Validate configuration values at startup.
- Add watchdog for long scan stalls.
- Auto-create local override config on startup when missing.
- Enforce sensitive data paths under user local sentineltray folder.
- Add privacy policy and tests for LGPD compliance.
- Add config error prompt with edit or exit option.
- Open status on left-click and refresh tray UI in PT-BR.
- Add Gmail SMTP example to local template.
- Add single-instance guard and installer script.
- Add email subject, retries, regex validation, and status export.
- Use eye icon and auto-open status window on startup.
- Add status shortcuts for config and repo, and switch eye color to light blue.
- Restore minimized windows before scanning.
- Add project title and description in the status UI.
- Add CSV export, config checksum, log-only mode, and disk free checks.

## 2026-01-14

- Initial notifier scaffold with window text detection and email senders.
- Update PyYAML dependency to support Python 3.14.
- Fix YAML regex quoting to prevent parse errors.
- Add system tray UI with live status window.
- Update Pillow dependency for Python 3.14 to 12.1.0.
- Remove Playwright dependency after switching to email.
- Add local override config path for sensitive settings.
- Rename project to SentinelTray.
- Apply GPL-3.0-only license.
- Remove chat_target from public configs.
- Enforce email as the only supported send mode.
- Auto-create and open local override config when missing or invalid.
- Create per-run detailed logs and retain only the last 5 files.
- Suppress noisy third-party debug logs in per-run files.
- Move local override config to %SENTINELTRAY_DATA_DIR% (portable).
- Add local template files with commented guidance.
