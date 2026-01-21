# Modelos locais

## Objetivo

Use estes arquivos como referência para criar os arquivos locais no computador do usuário.

## Como usar

1. Crie o arquivo de configuracao em:
   %USERPROFILE%\AppData\Local\AxonZ\SentinelTray\UserData\config.local.yaml
2. Preencha os campos obrigatorios e reinicie o aplicativo.
3. state.json é apenas um exemplo do formato de histórico local.

## Regex (curingas)

- `.*` corresponde a qualquer sequencia de caracteres.
- `.` corresponde a um unico caractere.
- `?` torna o caractere anterior opcional.
- `[A-Z]` corresponde a um conjunto/intervalo.
- `\d` para numeros, `\s` para espacos, `^` inicio e `$` fim.

Exemplos:

- window_title_regex: '^Sino\\.Siscam\\..*'
- phrase_regex: 'PROTOCOLOS?\\s+NAO\\s+RECEBIDOS'
- phrase_regex: 'ALERTA|CRITICO'

## Monitores multiplos

Use a chave `monitors` para definir varios pares de titulo + texto.
Cada item deve ter um bloco `email` completo.

## Observações

- Não inclua credenciais reais em arquivos de exemplo.
- Parâmetros adicionais de robustez disponíveis:
   - min_repeat_seconds
   - error_notification_cooldown_seconds
   - window_error_backoff_base_seconds / window_error_backoff_max_seconds
   - window_error_circuit_threshold / window_error_circuit_seconds
   - email_queue_file / email_queue_max_items / email_queue_max_age_seconds
   - email_queue_max_attempts / email_queue_retry_base_seconds
   - log_throttle_seconds
