# Política de Privacidade (LGPD)

## Objetivo

Esta aplicação processa dados pessoais apenas para enviar alertas e manter o histórico técnico de operação. O tratamento segue os princípios da LGPD, com foco em finalidade, necessidade, transparência e segurança.

## Dados pessoais tratados

- Endereços de e-mail de envio e recebimento.
- Credenciais SMTP (usuário e senha de app, quando aplicável).
- Conteúdo das mensagens de alerta que podem conter dados visíveis na janela monitorada.
- Nome do contato ou grupo configurado para envio via WhatsApp (quando habilitado).

## Base legal e finalidade

- Execução de contrato/legítimo interesse: alertas operacionais e diagnóstico local.
- Finalidade única: notificar eventos detectados na janela monitorada.

## Local de armazenamento

Dados sensiveis necessarios ao funcionamento ficam exclusivamente em:

- %SENTINELTRAY_DATA_DIR% (quando definido; run.cmd usa a pasta de instalacao)
- ou %LOCALAPPDATA%\AxonZ\SentinelTray\UserData (fallback padrao)

Isto inclui:

- config.local.yaml (credenciais e enderecos)
- state.json (histórico local)

Dados operacionais (diagnostico e status) ficam em:

- %SENTINELTRAY_DATA_DIR%\logs

- *.log (diagnostico)
- telemetry.json (estado operacional)
- status.json e status.csv (exportacao de status)
- config.checksum (integridade de configuracao)

O repositório contém apenas templates comentados e exemplos fictícios.

## Execução inicial

Ao iniciar, se %SENTINELTRAY_DATA_DIR%\config.local.yaml não existir, o aplicativo encerra com orientação de correção. O instalador copia um modelo de configuração quando o arquivo não existe. Dados pessoais permanecem apenas nesse diretório; logs operacionais permanecem em %SENTINELTRAY_DATA_DIR%\logs.

## Segurança e minimização

- Os dados são usados apenas para alertas e diagnóstico local.
- Não há envio para terceiros além do provedor SMTP configurado e/ou WhatsApp Desktop local.
- Campos sensíveis são mantidos fora do repositório e ignorados pelo controle de versão.
- Logs e exportações aplicam mascaramento de dados sensíveis (e-mails, telefones e caminhos locais).

## Retenção

- logs são mantidos apenas nas últimas 5 execuções (valores acima são limitados).
- state.json contém apenas o necessário para evitar duplicidade de envio.
- Filas locais de envio (quando habilitadas) seguem limites de quantidade e idade configurados.

## Direitos do titular

O usuário pode remover ou corrigir os dados a qualquer momento editando ou apagando os arquivos em %SENTINELTRAY_DATA_DIR%.

## Contato

Em caso de dúvidas sobre o tratamento, consulte o responsável pelo ambiente onde a aplicação foi instalada.

## Operadores e terceiros

- SMTP: depende do provedor configurado pelo usuário.
- WhatsApp: envio ocorre via aplicativo WhatsApp Desktop já instalado e logado.

## Segurança adicional

Relatórios automáticos de segurança e SBOM são gerados por release para apoiar auditorias, sem incluir dados pessoais.
