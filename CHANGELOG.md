# Changelog

## 2026-04-17 (5.0.0 rc.2)

- Correção: botão "Editar Config" agora cria o arquivo `config.local.yaml` com o template completo e comentado (lido do `.example` empacotado), em vez de um stub vazio de 2 linhas.

## 2026-04-17 (5.0.0 rc.1)

- Correção: assunto do e-mail de verificação manual sem resultado corrigido de "Correspondência Detectada" para "Verificação Manual" (nova categoria `verificação:` em `email_sender.py`).
- Correção: ponteiro solto em `dpapi_utils._bytes_to_blob` — buffer mantido vivo para evitar coleta prematura pelo GC durante operações DPAPI.
- Correção: `debounce_seconds` agora é sempre aplicado, independentemente de `send_repeated_matches`. Anteriormente, `send_repeated_matches=true` suprimia completamente o debounce, causando envio repetido a cada poll.
- Correção: remoção da injeção global de `VK_ESCAPE` em `detector._dismiss_shell_overlay`, que podia cancelar ações do usuário em outros aplicativos.
- Correção: adicionado cooldown de 30 segundos entre envios consecutivos do e-mail de "nenhuma correspondência" ao clicar em "Verificar Agora".
- Correção: padrão de `pause_on_user_active` corrigido de `False` para `True` em `_DEFAULT_CONFIG_VALUES`, alinhando código com documentação e arquivo `.example`.
- Correção: verificação SMTP na inicialização movida para thread de fundo (não bloqueia mais a inicialização por 10s) e estendida para todos os monitores configurados.
- Correção: `_terminate_existing_instance` agora verifica o nome do processo antes de executar `taskkill`, evitando encerrar processos não relacionados que por acaso tenham o mesmo PID.
- Correção: e-mail de healthcheck agora usa as configurações do monitor correspondente (janela e regex) em vez de sempre usar o monitor 1 para todos os envios.
- Correção: comentário de `healthcheck_interval_seconds` no arquivo de configuração corrigido de "900 (15 minutos)" para "1800 (30 minutos)".

## 2026-04-17 (4.3.6)

- Correção: template embutido `_CONFIG_TEMPLATE` em `entrypoint.py` sincronizado com `config.local.yaml.example`. O fallback agora gera um arquivo idêntico ao `.example` (em português, com todos os comentários e valores reais do projeto), eliminando a divergência de conteúdo que ocorria quando o arquivo `.example` não era encontrado durante a criação automática do `config.local.yaml`.

## 2026-04-17 (4.3.5)

- Correção: ao gerar `config.local.yaml` automaticamente na primeira execução do EXE compilado, o conteúdo agora corresponde corretamente ao `config.local.yaml.example` do projeto. O arquivo `.example` é incluído no pacote PyInstaller e lido via `sys._MEIPASS` em tempo de execução; o template genérico embutido em código é mantido apenas como fallback final.

## 2026-04-17 (4.3.0)

- Performance: `_select_best_window` usa `max()` em vez de `sorted()[0]`, reduzindo de O(n log n) para O(n) na seleção de janelas candidatas.
- Performance: `_normalize_text` usa list comprehension em vez de generator em `str.join`, eliminando overhead do protocolo de iteração na normalização Unicode.
- Performance: `datetime.now()` calculado uma única vez por iteração de monitor em `_scan_once_impl`, evitando chamada dupla quando debounce e min_repeat estão ambos ativos.

## 2026-04-17 (4.2.0)

- Config template: quando `config.local.yaml` não existe na inicialização, o arquivo criado automaticamente passa a usar o conteúdo exato de `config/config.local.yaml.example` (com comentários e valores reais do projeto), em vez do template genérico embutido em código. O template embutido é mantido como fallback caso o arquivo `.example` não seja encontrado.

## 2026-04-17 (4.1.0)

- Versão estável. Inclui todas as funcionalidades das versões 3.x e 4.0.0-rc.
- GUI: abre com a janela de status visível ao iniciar (não mais somente minimizada na bandeja).
- GUI: nome do autor exibido no rodapé da janela de status.
- Metadados: campo `authors` adicionado ao `pyproject.toml`; `__author__` exposto em `__init__.py`.
- Docs: README atualizado para versão 4.1.0 estável.
