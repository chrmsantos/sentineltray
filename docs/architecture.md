# Architecture

Versao beta: 0.2.0-beta.1 (19-01-2026)

## Overview

- Window text detection uses UI Automation via pywinauto.
- Minimized target windows are restored and focused before scanning.
- Email delivery uses SMTP with optional TLS.
- State is stored in state.json to prevent duplicate sends.
- Runtime is self-contained (embedded CPython + offline wheelhouse) managed by scripts/bootstrap_self_contained.cmd and validated by runtime/checksums.txt.
- Logs are created per execution with detailed fields and kept with a max of 5 files in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\SystemData\sentineltray\logs (values above 5 are capped).
- Third-party debug log noise is suppressed at the logger level.
- System tray UI shows status and controls exit.
- Errors in each polling iteration are reported on screen and via email immediately, even when log-only mode is enabled.
- When the target window is temporarily unavailable or disabled, an alert is sent and the scan is skipped.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- Tray icon is rendered via Pillow with fixed-size rectangle glyphs.
- Tray status shows error count and last error reason.
- Logs include a structured category field (scan/send/error/etc).
- Logs, telemetry, and status exports redact sensitive strings and store match summaries as hashes.
- Local telemetry file captures last activity for quick diagnostics and lives in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\SystemData\sentineltray\logs.
- Status export JSON supports local integrations.
- Status export CSV supports local integrations.
- Tray abre automaticamente o status na inicializacao e usa icone em formato de olho.
- Status inclui atalhos para abrir configuracoes e o repositorio.
- Interface exibe o nome e a descricao resumida do projeto no topo.
- Status inclui menu de comandos com pausar/continuar, encerrar e atalhos operacionais, com texto ampliado e amigavel, e janela ajustada ao conteudo.
- Escaneamento ocorre apenas após 2+ minutos sem interação do usuário.
- Assunto do e-mail sempre inclui SentinelTray, e o corpo começa com título SentinelTray em PT-BR.
- Correspondencia de frases ignora acentos, nao diferencia maiusculas/minusculas e aceita texto parcial dentro de textos maiores.
- Silent mode can suppress the error popup while keeping tray status updated.
- Email delivery failures are detected and reported as specific errors.
- SMTP authentication failures disable email sending for the session to avoid retries.
- Ambiguous window matches are resolved by selecting the most visible/focused candidate.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Sensitive data paths are enforced under %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData; operational logs remain in %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\SystemData\sentineltray\logs.
- Politica de privacidade detalhada em PRIVACY.md.
- Instalacao automatica disponivel via scripts/install.cmd.
- Config is loaded exclusively from %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\config.local.yaml.
- Missing, empty, or invalid local override triggers file creation and edit prompt.
- Local file templates live under templates/local/.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.
