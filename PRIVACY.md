# Privacy Policy (LGPD)

## Purpose

This application processes personal data only to send alerts and maintain the technical operating history. Processing follows LGPD principles with a focus on purpose limitation, necessity, transparency, and security.

## Personal data processed

- Sender and recipient email addresses.
- SMTP credentials (username and app password, when applicable).
- Alert message content, which may include data visible in the monitored window.

## Legal basis and purpose

- Contract performance/legitimate interest: operational alerts and local diagnostics.
- Single purpose: notify events detected in the monitored window.

## Storage location

Sensitive data required for operation is stored exclusively in:

- %SENTINELTRAY_DATA_DIR% (when defined)
- or %LOCALAPPDATA%\AxonZ\SentinelTray\config (default fallback)

This includes:

- config.local.yaml (credentials and addresses)
- state.json (local history)

Encrypted configs (config.local.yaml.enc) are supported via Windows DPAPI to protect sensitive data at rest. On startup, the app attempts to encrypt plaintext configs.
The tray config editor uses a temporary plaintext file in the local data directory and removes it after re-encrypting.

Operational data (diagnostics and status) is stored in:

- %SENTINELTRAY_DATA_DIR%\logs

- *.log (diagnostics)
- telemetry.json (operational state)
- status.json and status.csv (status exports)
- config.checksum (configuration integrity)

The repository contains only commented templates and fictitious examples.

## Initial execution

On startup, if %SENTINELTRAY_DATA_DIR%\config.local.yaml does not exist, the application exits with correction guidance. Personal data remains only in that directory; operational logs remain in %SENTINELTRAY_DATA_DIR%\logs.

## Security and minimization

- Data is used only for alerts and local diagnostics.
- There is no sharing with third parties beyond the configured SMTP provider.
- Sensitive fields are kept out of the repository and ignored by version control.
- Logs and exports apply masking for sensitive data (emails, phone numbers, and local paths).

## Retention

- Logs are kept only for the last 5 runs (higher values are capped).
- state.json contains only what is required to avoid duplicate sends.
- Local send queues (when enabled) follow the configured quantity and age limits.

## Data subject rights

The user can remove or correct data at any time by editing or deleting files under %SENTINELTRAY_DATA_DIR%.

## Contact

For questions about processing, consult the person responsible for the environment where the application was installed.

## Operators and third parties

- SMTP: depends on the provider configured by the user.

## Additional security

Internal reports do not include personal data.
