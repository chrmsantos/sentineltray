# Architecture

Versao beta: 1.0.0-beta.2 (22-01-2026)

## Overview

- Window text detection uses UI Automation via pywinauto.
- Minimized target windows are restored and focused before scanning.
- Email delivery uses SMTP with optional TLS.
- State is stored in state.json to prevent duplicate sends.
- Runtime is self-contained (embedded CPython + offline wheelhouse) validated by runtime/checksums.txt.
- Logs are created per execution with detailed fields and kept with a max of 5 files in %SENTINELTRAY_DATA_DIR%\logs (values above 5 are capped).
- Third-party debug log noise is suppressed at the logger level.
- Errors in each polling iteration are reported via email immediately, even when log-only mode is enabled.
- When the target window is temporarily unavailable or disabled, an alert is sent and the scan is skipped.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Logs include a structured category field (scan/send/error/etc).
- Logs, telemetry, and status exports redact sensitive strings and store match summaries as hashes.
- Logs are emitted in both text and JSONL formats for easier ingestion.
- Telemetry, status exports, and state storage are written atomically to avoid corruption on abrupt shutdown.
- Export files include counters for write failures (telemetry/status CSV/state) to aid diagnostics.
- Local telemetry file captures last activity for quick diagnostics and lives in %SENTINELTRAY_DATA_DIR%\logs.
- Status export JSON supports local integrations.
- Status export CSV supports local integrations.
- Releases publicam provenance (SLSA).
- Status updates are available via log files and status exports.
- Escaneamento ocorre apenas após 2+ minutos sem interação do usuário.
- Assunto do e-mail sempre inclui SentinelTray, e o corpo começa com título SentinelTray em PT-BR.
- Correspondencia de frases ignora acentos, nao diferencia maiusculas/minusculas e aceita texto parcial dentro de textos maiores.
- Email delivery failures are detected and reported as specific errors.
- SMTP authentication failures disable email sending for the session to avoid retries.
- Ambiguous window matches are resolved by selecting the most visible/focused candidate.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Sensitive data paths are enforced under %SENTINELTRAY_DATA_DIR%; operational logs remain in %SENTINELTRAY_DATA_DIR%\logs.
- Politica de privacidade detalhada em PRIVACY.md.
- Dados locais residem em %SENTINELTRAY_DATA_DIR% (portable), com fallback para %LOCALAPPDATA%.
- Config is loaded exclusively from %SENTINELTRAY_DATA_DIR%\config.local.yaml.
- Missing, empty, or invalid local override triggers file creation and edit prompt.
- Local file templates live under templates/local/.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.

## Comportamentos críticos

- Idle gate: só escaneia após 2+ minutos sem interação do usuário.
- Backoff: erros consecutivos aumentam o intervalo até o máximo configurado.
- Watchdog: reinicia componentes se um ciclo exceder o timeout configurado.
- Persistência: falhas de escrita são contadas e expostas nos exports.
