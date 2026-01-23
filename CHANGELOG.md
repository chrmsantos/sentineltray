# Changelog

## Unreleased

- Remove legacy security automation workflows and documentation.
- Remove legacy alternate delivery channel and related UI/config/test coverage.
- Remove GUI/tray interface and related configuration/tests.
- Add portable encryption with local key support and offline dependency bootstrap for bundled runtime.
- Improve logging for platform limits and SMTP failures.
- Add /nonportable switch to allow system Python when portable runtime is unavailable.
- Add prepare_portable_runtime script to download embeddable Python and wheels.
- Auto-run portable runtime preparation from run.cmd when runtime is missing.
- Harden portable runtime preparation when pip or wheel download fails.
- Make bootstrap runtime install pip when missing.
- Use Scripts\\pip.exe fallback when embedded Python cannot import pip.
- Ensure embedded runtime ._pth enables site-packages for pip bootstrap.
- Auto-download missing wheels when wheelhouse is incomplete.

## 2026-01-22 (1.0.0-beta.2)

- Improve visibility timeout handling to reduce false warnings when the target window reports visible/enabled after retries.
- Stabilize scan preparation by refocusing and clicking the title bar to reduce interference from temporary overlays.
- Add manual scan, update/restart options, and startup validation of monitored window availability.
- Add security documentation, issue/PR templates, release checklist, and SLSA provenance for releases.
- Add mypy type checking configuration and CI step.

## 2026-01-21 (1.0.0-beta.1)

- Use atomic writes for telemetry, status exports, state storage, and config checksums to prevent corruption on abrupt shutdown.
- Restore CLI entrypoint module to resolve missing import at startup.
- Add write failure counters to exports and improve runtime preflight checks.
- Make window visibility checks more tolerant to avoid false unavailable errors.
- Adjust alert email wording for detected text.
- Stop auto-creating config templates; report configuration errors with explicit guidance and exit.
- Add multi-monitor support with per-monitor email settings and regex usage guidance.

## 2026-01-20 (0.2.0-beta.7)

- Move sensitive user data and operational logs/status to %SENTINELTRAY_DATA_DIR% (portable) with fallback to %LOCALAPPDATA%\AxonZ\SentinelTray\config.
- Redact sensitive data from logs, status exports, and telemetry while preserving diagnostic utility.
- Add status report emails every 7 scan iterations and surface last_report_send in exports/UI.
- Set default scan interval to 3 minutes in templates.
- Add runtime checksum validation, stricter log path validation, and Windows mutex for single-instance stability.
- Improve window detection retries and expand log redaction for tokens/phones.
- Load configuration exclusively from config.local.yaml and reject overrides.

## 2026-01-19 (0.2.0-beta.6)

- Store operational logs, telemetry, and status exports under the project logs/ folder; sensitive data remains in %SENTINELTRAY_DATA_DIR%.
- Allow running main.py directly by bootstrapping src/ onto the import path.

## 2026-01-23 (1.0.0-beta.3)

- Add tray config editor with auto-encryption after editing.
- Remove CLI and expose only Config/Exit from the tray icon.
- Rename UserData folder to config across defaults and docs.
- Add per-user startup registration via scripts/run.cmd.

## 2026-01-23 (0.2.0-beta.6)

- Add tray icon with CLI launcher (left-click opens CLI, right-click shows Open/Exit).
- Add interactive CLI with pause/resume/scan/status/exit commands.
- Protect user config with Windows DPAPI encryption and auto-encrypt plaintext configs.

## 2026-01-19 (0.2.0-beta.5)

- Disable email sending for the session after SMTP authentication failure to prevent repeated retries.
- Resolve ambiguous window matches by selecting the most visible/focused candidate.

## 2026-01-19 (0.2.0-beta.4)

- Send user alerts when the target window is unavailable and skip that scan.

## 2026-01-19 (0.2.0-beta.3)

- Ensure error notifications always attempt immediate email delivery.

## 2026-01-19 (0.2.0-beta.2)

- Move local user data directory to %SENTINELTRAY_DATA_DIR% (portable) for configs, logs, and telemetry.
- Skip scans without error alerts when the target window is unavailable or disabled.

## 2026-01-19 (0.2.0-beta.1)

- Enforce log retention caps at 5 files, clamping higher configured values.
- Gate scans to run only after 2+ minutes of user inactivity.
- Ensure email subjects always include SentinelTray and bodies use friendly English text.
- Make phrase matching accent-insensitive with partial text detection.
- Make phrase matching case-insensitive.

## 2026-01-16

- Report per-iteration monitoring errors on screen and via email.
- Send a startup email test message on each run.
- Add periodic healthcheck summaries via email.
- Add exponential backoff for consecutive errors.
- Debounce repeated messages within a time window.
- Add structured log categories.
- Add local telemetry file for diagnostics.
- Detect email delivery failures.
- Validate configuration values at startup.
- Add watchdog for long scan stalls.
- Auto-create local override config on startup when missing.
- Enforce sensitive data paths under user local sentineltray folder.
- Add privacy policy and tests for LGPD compliance.
- Add Gmail SMTP example to local template.
- Add email subject, retries, regex validation, and status export.
- Restore minimized windows before scanning.
- Add CSV export, config checksum, log-only mode, and disk free checks.

## 2026-01-14

- Initial notifier scaffold with window text detection and email senders.
- Update PyYAML dependency to support Python 3.14.
- Fix YAML regex quoting to prevent parse errors.
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
