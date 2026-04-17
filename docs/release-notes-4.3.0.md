# Release notes — 4.3.0 (2026-04-17)

## Destaques

Versão **estável** focada em melhorias de desempenho no caminho crítico de varredura, sem alterações de comportamento ou risco de regressão.

## Novidades nesta versão

- **Performance — seleção de janelas candidatas**: `_select_best_window` substituiu `sorted(..., reverse=True)[0]` por `max(...)`, reduzindo a complexidade de O(n log n) para O(n) ao escolher a melhor janela entre múltiplas candidatas.
- **Performance — normalização Unicode**: `_normalize_text` substituiu o generator em `str.join` por uma list comprehension. O `str.join` pré-aloca o buffer interno quando recebe uma lista, eliminando o overhead do protocolo de iteração. Esta função é chamada para cada elemento de texto de cada descendente de janela em cada varredura.
- **Performance — relógio por iteração de monitor**: `datetime.now(timezone.utc)` é calculado uma única vez por monitor em `_scan_once_impl` e reutilizado pelos filtros `filter_debounce` e `filter_min_repeat`, eliminando a chamada duplicada que ocorria quando ambos os filtros estavam ativos simultaneamente.
