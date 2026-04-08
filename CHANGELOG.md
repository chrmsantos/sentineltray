# Changelog

## 2026-04-08 (3.1.0-rc.1)

- Scan: pausado automaticamente quando o usuário está ativo (idle < threshold).
- Config: novas opções `pause_on_user_active` (padrão: true) e `pause_idle_threshold_seconds` (padrão: 180).
- Scan manual: ignora a pausa por atividade do usuário.

## 2026-03-18 (3.0.0)

- CLI: console redesenhado automaticamente após cada scan sem interação do usuário.
- Scan não intrusivo: janela é restaurada ao estado original após a leitura.
- Múltiplos monitores: limite de monitor único removido.
- Alertas com delta: variação numérica (+N/-N) incluída nas mensagens de alerta.
- Healthcheck e startup test ativos com e-mail de confirmação.
- Verificação de espaço em disco (aviso abaixo de 50 MB).
- Flags `--version` e `--help` disponíveis na linha de comando.
- Validação de porta SMTP e aviso de senha plaintext no YAML.
- PID validado antes de `taskkill`.
- Dependência `ruamel.yaml` removida.
- `.gitignore` endurecido; template de config comitado.

## 2026-02-06 (3.0.0-rc.3)

- Console: last scan result is now shown in the header.
- Console: config editor now edits the project config file directly.
- Monitoring: only monitor 1 is used; extra monitors are ignored.
- Runtime: prevents sleep/display power-down while running.
- Console: suppresses console logs to keep the UI stable.

## 2026-02-05 (3.0.0-rc.2)

- Window detection: title regex now matches partial titles (regex search) to avoid missing dynamic titles.
- Console: added window match listing action to validate title regex against open windows.
- Console: header shows last scan timestamp and last error for quicker diagnostics.
- SMTP: missing passwords prompt at startup and allow auth reset without restarting the app.
- Dependencies: clearer error when pywinauto is missing instead of masking it as a lookup failure.

## 2026-02-04 (3.0.0-rc.1)

- Startup: added integrity checks for data/log directories, portable runtime markers, and automatic config template reconciliation.
- SMTP: username now comes only from config.local.yaml; password is prompted at startup for every configured username.

## 2026-02-03 (beta.10)

- Notifications: drop info-category emails to avoid "SentinelTray Info" subjects.
- Scanning: when the target window is open, restore if minimized, then enforce foreground and maximized before scanning.
- Console: status header now shows EXECUTANDO/PARADO, error count, and last message sent indicator.
- Console: display includes ERROS count and última mensagem line in the status header.
- Security: SMTP password must come from SENTINELTRAY_SMTP_PASSWORD; config secrets are rejected.
- Logging: retention capped to 3 files and scan_id added to text/JSON logs; info logs are deduplicated.
- Config: first run requires dry_run=true unless log-only mode is enabled.
- Console: config error screen can prompt for SMTP env variables and retry.

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
