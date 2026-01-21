# Política de Privacidade (LGPD)

## Objetivo

Esta aplicação processa dados pessoais apenas para enviar alertas e manter o histórico técnico de operação. O tratamento segue os princípios da LGPD, com foco em finalidade, necessidade e segurança.

## Dados pessoais tratados

- Endereços de e-mail de envio e recebimento.
- Credenciais SMTP (usuário e senha de app, quando aplicável).
- Conteudo das mensagens de alerta que podem conter dados visiveis na janela monitorada.

## Local de armazenamento

Dados sensiveis necessarios ao funcionamento ficam exclusivamente em:

%USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData

Isto inclui:

- config.local.yaml (credenciais e enderecos)
- state.json (histórico local)

Dados operacionais (diagnostico e status) ficam em:

%USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\logs

- *.log (diagnostico)
- telemetry.json (estado operacional)
- status.json e status.csv (exportacao de status)
- config.checksum (integridade de configuracao)

O repositório contém apenas templates comentados e exemplos fictícios.

## Execução inicial

Ao iniciar, se %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\config.local.yaml não existir, o aplicativo cria o arquivo e o abre para preenchimento inicial. Dados pessoais permanecem apenas nesse diretório; logs operacionais permanecem em %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\logs.

## Segurança e minimização

- Os dados são usados apenas para alertas e diagnóstico local.
- Não há envio para terceiros além do provedor SMTP configurado.
- Campos sensíveis são mantidos fora do repositório e ignorados pelo controle de versão.

## Retenção

- logs são mantidos apenas nas últimas 5 execuções.
- state.json contém apenas o necessário para evitar duplicidade de envio.

## Direitos do titular

O usuário pode remover ou corrigir os dados a qualquer momento editando ou apagando os arquivos em %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData.

## Contato

Em caso de dúvidas sobre o tratamento, consulte o responsável pelo ambiente onde a aplicação foi instalada.
