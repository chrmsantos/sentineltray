# Release notes — 4.0.0-rc.1 (2026-04-16)

## Destaques

Esta é uma versão candidata a lançamento (RC) com foco na **nova interface gráfica completa**, substituindo definitivamente a interface de console pela janela de status em tema GitHub-dark e pelo editor de configuração integrado.

## Mudanças

### Nova interface gráfica (GUI)

- **`src/sentineltray/gui_app.py`** (novo módulo): ponto de entrada GUI que substitui `console_app` no caminho normal de execução.
- **Janela de status** (`StatusWindow`): layout de duas colunas para monitores widescreen (1080×580, redimensionável, mínimo 900×480).
  - Coluna esquerda: indicador de status com ponto colorido (EXECUTANDO / PARADO / INICIANDO), tempo ativo (TEMPO ATIVO), seção VERIFICAÇÃO e seção ALERTAS.
  - Coluna direita: seção ERROS, painel FILA DE E-MAIL com contadores coloridos e seção MONITORES com estado de cada monitor.
  - Cabeçalho com logotipo olho animado, nome do app, subtítulo e versão + data de build.
  - Rodapé com botões: **⟳ Verificar Agora**, **⚙ Configuração**, **↗ Repositório**, **Sair ✕**.
- **Título da janela**: exibe versão e data de build (`SentinelTray 4.0.0-rc.1 (16-04-2026) — Status`).
- App inicia sempre minimizado na bandeja; a janela só aparece via tray ou clique duplo.

### Editor de configuração integrado

- **`ConfigEditorWindow`**: editor modal `tk.Toplevel` abre ao clicar em **⚙ Configuração**.
  - Editor `Consolas 11` com gutter de números de linha sincronizado, scrollbars horizontal e vertical.
  - Barra de status com feedback em tempo real: cinza (Pronto), âmbar (Alterações não salvas), verde (válido), vermelho (erro de validação).
  - **Validar**: analisa o YAML em arquivo temporário sem tocar no arquivo real.
  - **Salvar e Aplicar**: valida → grava → recarrega a configuração em memória sem reiniciar o app.
  - Atalhos de teclado: `Ctrl+S` = Salvar e Aplicar, `Escape` = Cancelar.
  - Elimina a dependência do Bloco de Notas para edição de configuração.

### Bandeja do sistema

- **`src/sentineltray/tray_app.py`**: modo GUI com menu simplificado — **Abrir Status** (ação padrão) + separador + **Sair**.
- Console permanece oculto no modo GUI; sem flash de terminal ao iniciar.

### Build

- **`SentinelTray.spec`**: `console=False` — elimina completamente o flash do console ao iniciar.

### Localização

- Interface totalmente em português do Brasil: todos os rótulos, botões, mensagens de status, seções de card e itens do menu da bandeja.

### Entrypoint

- **`src/sentineltray/entrypoint.py`**: caminho normal chama `run_gui(config)` em vez de `run_console(config)`.
- Caminho de erro de configuração continua usando `run_console_config_error` para exibir detalhes no console.
