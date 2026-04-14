# Changelog

## 2026-04-14 (3.4.5)

- CLI: endereço de e-mail do remetente agora é atualizado corretamente quando alterado no editor de configuração.

## 2026-04-14 (3.3.0)

- Console: janela não é mais minimizada automaticamente ao iniciar; o app abre normalmente na barra de tarefas.
- Scan: monitoramento executa continuamente independente da atividade do usuário (`pause_on_user_active` agora é `false` por padrão).
- Scan: menu Iniciar do Windows (Start menu) não causa mais o erro "Target window not in foreground"; o app detecta e descarta o overlay do shell antes de retomar o foco.
- CLI: novo comando `[T] Mensagem teste` — envia uma mensagem de teste sob demanda (funcionalidade antes executada automáticamente no startup).
- Config: arquivo `config.local.yaml` é criado automaticamente a partir de um template comentado caso não exista; o Bloco de Notas abre o arquivo para preenchimento.
- E-mail: todos os textos das mensagens enviadas traduzidos para português do Brasil.

## 2026-04-09 (3.2.0-rc.2)

- Tray: app inicia sempre minimizado na bandeja do sistema (sem flash do console).
- Tray: fechar (×) a janela do console minimiza para a bandeja em vez de encerrar o processo.

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
