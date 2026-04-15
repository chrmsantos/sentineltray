# Release notes — 3.5.7 (2026-04-15)

## Highlights

- Diretório de dados do usuário padronizado em `%LOCALAPPDATA%\ZWave\Tmp\SentinelTray\Config`.

## Mudanças

- **Caminho de configuração**: `get_user_data_dir()` agora resolve para `%LOCALAPPDATA%\ZWave\Tmp\SentinelTray\Config` em vez de `%USERPROFILE%\ZWave\Apps\Tmp`. A variável de ambiente `SENTINELTRAY_DATA_DIR` continua sendo honrada quando definida explicitamente.
- **Arquivos afetados**: `config.local.yaml`, `state.json`, senhas SMTP (`.dpapi`), logs e fila de e-mail são gravados e lidos exclusivamente do novo caminho.
