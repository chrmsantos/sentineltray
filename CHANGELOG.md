# Changelog

## 2026-04-29 (5.7.0)

- Qualidade: refatoração abrangente de boas práticas Python em todos os 21 módulos do pacote `z7_sentineltray` — docstrings no estilo Google, anotações de tipo completas, anti-padrões corrigidos (TRY/SIM/N/C90/ANN/RUF).
- Qualidade: configuração de ferramentas adicionada ao `pyproject.toml` — Ruff (linter + formatter, 0 erros em `src/` e `tests/`), mypy em modo estrito, pre-commit hooks (ruff + mypy + formatadores padrão).
- Qualidade: marcador PEP 561 `py.typed` adicionado ao pacote para sinalizar suporte a type-checking estático.
- Qualidade: suite de testes aprimorada — PT017/PT011/SIM105/N802/E402 corrigidos nos arquivos de teste; arquivo de conflito duplicado removido; 144 testes passando.
- Limpeza: artefatos de saída de build e testes (`.txt`) removidos da raiz do projeto; `.gitignore` atualizado com padrões para prevenir reacumulação.

## 2026-04-29 (5.6.2)

- Melhoria: qualidade visual do ícone do app aprimorada — supersampling elevado de 4× para 6×; limbal ring adicionado ao redor da íris; textura de fibras radiais (28 raios) na íris; segundo reflexo de luz na pupila; arco de pálpebra superior separado; 7 cílios com comprimento variável; sombra projetada sob o olho; brilho em duas camadas (haze amplo + núcleo quente); esclera com branco levemente quente; fundo com vignette central sutil.

## 2026-04-28 (5.6.1)

- Correção: ícone do app revertido para o olho verde (design original) — substitui a torre sentinela introduzida na 5.6.0; `generate_icon.py` reescrito para produzir o olho com supersampling 4×, íris multicamada, pupila e reflexo de luz.
- Novo: testes de persistência do tema claro/escuro (`test_theme_persistence.py`) — 8 casos cobrindo padrão escuro, round-trip salvar/carregar, fallback em arquivo corrompido e criação automática do diretório de configuração.
- Correção: BOM UTF-8 removido de `pyproject.toml`, que impedia o pytest de ler o arquivo de configuração TOML.

## 2026-04-28 (5.6.0)

- Correção: corpo dos e-mails agora sempre enviado em UTF-8 (`charset="utf-8"` em `email.set_content`), corrigindo caracteres corrompidos (`\xe7\xe3`, `\xfa`, etc.) em clientes de e-mail Windows.
- Novo: ícone do app substituído por torre sentinela com holofote e janela de farol verde (supersampling 4× + LANCZOS, multi-resolução 16–256px).
- Novo: botão "✉ Destinatários" no rodapé da janela de status — permite editar `to_addresses` de todos os monitores diretamente na interface, sem abrir o editor completo de configuração.
- Limpeza: removidas referências a `config.local.yaml.enc` e `config.local.key` do `.gitignore`; arquivos residuais deletados (esquema de criptografia de config era artefato morto).

## 2026-04-24 (5.5.0)

- Novo: switcher claro/escuro na barra de rodapé da janela de status — alterna entre o tema escuro (GitHub-dark) e o tema claro (GitHub-light) em tempo real. A preferência é persistida em `ui_prefs.json` e restaurada na próxima abertura.
- Novo: todos os textos dos e-mails enviados ao usuário (alertas, erros, healthcheck, verificação manual) traduzidos para o português do Brasil. O corpo do healthcheck agora exibe rótulos como "Janela monitorada", "Última verificação", "Disjuntores ativos", etc.
- Correção: caminhos do arquivo `Z7_SentinelTray.spec` atualizados para o diretório correto do projeto (`Z7\Apps\Z7_SentinelTray`).

## 2026-04-24 (5.4.0)

- Release: projeto renomeado para Z7_SentinelTray (pacote Python `z7_sentineltray`).
- Promoção do candidato 5.4.0 rc.1 para versão estável.

## 2026-04-18 (5.1.0)

- Novo: botão "Restaurar valores padrão" no editor de configuração — restaura o conteúdo do editor para o template oficial (`config.local.yaml.example`) com confirmação prévia.
- Novo: na primeira inicialização sem `config.local.yaml`, o app abre o editor gráfico de configuração pré-preenchido com os valores padrão, em vez de abrir o Bloco de Notas e encerrar.

## 2026-04-17 (5.0.1 rc.1)

- Correção: janela GUI de edição de configuração (`ConfigEditorWindow`) agora cria `config.local.yaml` com o template completo (lido do `.example` empacotado) quando o arquivo não existe, em vez de um stub de uma linha.

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
