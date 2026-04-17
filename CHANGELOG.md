# Changelog

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
