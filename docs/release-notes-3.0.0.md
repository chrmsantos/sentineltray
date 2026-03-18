# Release notes — 3.0.0 (2026-03-18)

## Highlights

Esta é a primeira versão estável do SentinelTray 3.x.

## Novidades desde 3.0.0-rc.3

- **CLI com atualização automática**: o console é redesenhado automaticamente
  após cada ciclo de scan sem necessidade de pressionar Enter.
- **Scan não intrusivo**: a janela monitorada é restaurada ao estado original
  (minimizada e foco devolvido ao aplicativo anterior) após a leitura.
- **Múltiplos monitores habilitados**: o limite de um monitor foi removido;
  todos os monitores configurados são ativados.
- **Delta em alertas**: mensagens de alerta incluem a variação `+N / -N`
  em relação ao último scan quando o texto possui contador numérico.
- **Healthcheck ativo**: e-mail de status periódico agora é enviado com
  subject "SentinelTray — Status do sistema".
- **Startup test ativo**: mensagem de confirmação de início enviada por e-mail.
- **Verificação de espaço em disco**: aviso de log quando menos de 50 MB livres.
- **Módulo `idle_utils`**: utilitário multiplataforma seguro para leitura
  inteligente de tempo ocioso do sistema.
- **Flags de linha de comando**: `--version` / `-V` e `--help` / `-h` disponíveis.
- **Validação de porta SMTP**: porta inválida (fora de 1–65535) rejeitada na carga.
- **Aviso de senha plaintext**: credenciais SMTP em texto puro no YAML geram
  aviso de log pedindo migração para o armazenamento DPAPI.
- **PID validado antes de `taskkill`**: valores absurdos de PID são rejeitados
  para evitar encerramento acidental de processos do sistema.
- **Segurança**: `.gitignore` endurecido; nenhum dado sensível de runtime
  é rastreado pelo Git.
- **Template de config**: `config/config.local.yaml.example` comitado como
  referência completa e segura para novos usuários.
- **Tray icon (scaffolded)**: estrutura de `tray_app.py` inclusa para uso futuro.

## Mudanças internas

- `_build_subject` reconhece a categoria `healthcheck` e formata subject correto.
- `scan_context` e `log_context` corretamente tipados como `Iterator[None]`.
- `_resolve_level` usa `logging.getLevelNamesMapping()` (API pública, Python ≥ 3.11).
- Leitura bloqueante do console substituída por loop não-bloqueante com `msvcrt`.
- Dependência `ruamel.yaml` removida.
