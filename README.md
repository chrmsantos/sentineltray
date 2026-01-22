# SentinelTray

Versão beta: 1.0.0-beta.1 (21-01-2026)

Minimal Windows notifier that reads visible text from a target desktop app and sends an email when a phrase appears.

## Requirements

- Windows user session (no admin required).
- SMTP server access for email delivery.

## Setup (self-contained)

1. Bootstrap the bundled runtime (totalmente offline):

   ```powershell
   scripts\bootstrap_self_contained.cmd
   ```

   This validates the embedded CPython and dependencies already bundled in runtime/.
   Checksums are stored in runtime/checksums.txt and validated on startup.

2. Edit config.local.yaml and set:

- window_title_regex (prefixo unico do titulo e suficiente)
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- email.smtp_host
- email.from_address
- email.to_addresses
- email.subject
- email.retry_attempts
- email.retry_backoff_seconds
- email.dry_run = false when ready to send
- status_export_csv, status_refresh_seconds, allow_window_restore, start_minimized, send_repeated_matches
- log_only_mode, config_checksum_file, min_free_disk_mb
- log_level, log_console_level, log_console_enabled
- log_max_bytes, log_backup_count, log_run_files_keep
- min_repeat_seconds, error_notification_cooldown_seconds
- window_error_backoff_base_seconds, window_error_backoff_max_seconds
- window_error_circuit_threshold, window_error_circuit_seconds
- email_queue_file, email_queue_max_items, email_queue_max_age_seconds
- email_queue_max_attempts, email_queue_retry_base_seconds
- log_throttle_seconds

The application always reads the local config file. Default location is driven by
`SENTINELTRAY_DATA_DIR` when set (run.cmd sets it to the install folder for a
portable, self-contained setup). Otherwise it falls back to:

- %LOCALAPPDATA%\AxonZ\SentinelTray\UserData\config.local.yaml

If config.local.yaml is missing, empty, or invalid, the app creates it,
opens it for editing, and exits so you can fill it.

Local documentation for sample state files lives under templates/local/.

## Instalacao automatica (Windows CMD)

Use o script em scripts/install.cmd (arquivo unico/standalone) para baixar o projeto
do GitHub e instalar o runtime auto-contido (CPython embutido + dependencias já inclusas).
O instalador gera logs em %TEMP%\sentineltray-install e mantém apenas os 5 mais recentes.
Durante a instalacao, um atalho SentinelTray.lnk e criado em shortcuts/ e copiado
para a área de trabalho do usuário.
Destino de instalacao: %USERPROFILE%\AxonZ\SystemData\sentineltray.
Os dados locais ficam dentro da pasta de instalacao em UserData\ (modo portable) e
podem ser movidos definindo SENTINELTRAY_DATA_DIR.

Opcoes:

- /offline /zip arquivo.zip (instalacao offline com zip local)
- /dir pasta (define diretorio de instalacao)
- /sha256 hash (valida integridade do zip)
- /update (atualiza preservando rollback)
- /uninstall (desinstala)
- /no-desktop (nao cria atalho na area de trabalho)
- /no-startmenu (nao cria atalho no Menu Iniciar)

Para desinstalar:

scripts\uninstall.cmd

## Run

scripts\run.cmd

If you run main.py directly, it automatically adds src/ to the import path.

SentinelTray inicia em segundo plano com um ícone na bandeja do sistema.
Clique com o botão esquerdo para abrir o painel de status.
Clique com o botão direito para Abrir ou Sair.

O painel exibe o status completo do sistema e atualiza a cada 10 segundos.
Use a barra de menus para ações e atalhos (configurações, logs, dados e site).

## Regex (curingas) e exemplos

Use regex nas strings de titulo/nome da janela e no texto a procurar. Dicas:

- `.*` corresponde a qualquer sequencia de caracteres.
- `.` corresponde a um unico caractere.
- `?` torna o caractere anterior opcional.
- `[A-Z]` corresponde a um conjunto/intervalo.
- `\d` para numeros, `\s` para espacos, `^` inicio e `$` fim.

Exemplos:

- window_title_regex: 'Siscam.*Desktop'
- window_title_regex: '^Sino\\.Siscam\\..*'
- phrase_regex: 'PROTOCOLOS?\\s+NAO\\s+RECEBIDOS'
- phrase_regex: 'ALERTA|CRITICO'

## Monitores multiplos (titulo + texto + email)

Para monitorar mais de um par titulo + texto, use `monitors`.
Cada item deve ter sua propria configuracao de email.
Quando `monitors` for usado, o bloco `email` no topo pode ser omitido.

Exemplo:

```yaml
monitors:
   - window_title_regex: 'APP1'
      phrase_regex: 'ALERTA1'
      email:
         smtp_host: 'smtp.local'
         smtp_port: 587
         smtp_username: ''
         smtp_password: ''
         from_address: 'alerts1@example.com'
         to_addresses: ['ops1@example.com']
         use_tls: true
         timeout_seconds: 10
         subject: 'SentinelTray Notification'
         retry_attempts: 0
         retry_backoff_seconds: 0
         dry_run: true
   - window_title_regex: 'APP2'
      phrase_regex: 'ALERTA2'
      email:
         smtp_host: 'smtp.local'
         smtp_port: 587
         smtp_username: ''
         smtp_password: ''
         from_address: 'alerts2@example.com'
         to_addresses: ['ops2@example.com']
         use_tls: true
         timeout_seconds: 10
         subject: 'SentinelTray Notification'
         retry_attempts: 0
         retry_backoff_seconds: 0
         dry_run: true
```

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in %SENTINELTRAY_DATA_DIR%\logs (values above 5 are capped).
- Logs rotate by size using log_max_bytes and log_backup_count.
- JSON logs are written alongside text logs in sentineltray.jsonl and per-run sentineltray_*.jsonl.
- Script logs (install/run/bootstrap) are stored under %SENTINELTRAY_DATA_DIR%\logs\scripts.
- Third-party debug logs are suppressed to keep logs actionable.
- Logs, telemetry, and status exports redact sensitive strings (emails and local paths) and store match summaries as hashes.
- Runtime artifacts are integrity-checked via runtime/checksums.txt.
- state.json stores the last sent messages to avoid duplicates.
- Errors detected in each polling iteration are reported on screen and via email immediately.
- When the target window is unavailable or disabled, an alert is sent and the scan is skipped.
- Monitor failures use a per-monitor circuit breaker and local backoff to avoid alert storms.
- Email delivery failures are queued locally and retried with exponential backoff.
- Error notifications are rate-limited via error_notification_cooldown_seconds.
- A startup test message is sent via email on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via email.
- Janelas minimizadas sao restauradas para leitura do texto.
- Phrase matching ignores accents, is case-insensitive, and matches partial text occurrences.
- Consecutive errors trigger exponential backoff before the next scan.
- Repeated messages are debounced by time window to avoid spam.
- send_repeated_matches still respects min_repeat_seconds if configured.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
- Logs include a structured category field.
- Local telemetry file captures last activity for quick diagnostics and lives in %SENTINELTRAY_DATA_DIR%\logs.
- Status export JSON available at status_export_file (UserData\logs by default).
- Status export CSV available at status_export_csv (UserData\logs by default).
- Log-only mode skips normal alert sends but still emails error notifications.
- Email delivery failures are detected and reported as specific errors.
- Email subject always includes SentinelTray, and the body starts with a SentinelTray title in PT-BR.
- Config validation rejects invalid intervals and paths at startup.
- Watchdog detects long scans and can reset components.
- Scans run only after 2+ minutes of user inactivity.
- Sensitive data is always stored under %SENTINELTRAY_DATA_DIR%; operational logs stay in %SENTINELTRAY_DATA_DIR%\logs.
- Política de privacidade em PRIVACY.md.
