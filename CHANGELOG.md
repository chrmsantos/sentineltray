# Changelog

## 2026-04-17 (4.2.0)

- Config template: quando `config.local.yaml` não existe na inicialização, o arquivo criado automaticamente passa a usar o conteúdo exato de `config/config.local.yaml.example` (com comentários e valores reais do projeto), em vez do template genérico embutido em código. O template embutido é mantido como fallback caso o arquivo `.example` não seja encontrado.

## 2026-04-17 (4.1.0)

- Versão estável. Inclui todas as funcionalidades das versões 3.x e 4.0.0-rc.
- GUI: abre com a janela de status visível ao iniciar (não mais somente minimizada na bandeja).
- GUI: nome do autor exibido no rodapé da janela de status.
- Metadados: campo `authors` adicionado ao `pyproject.toml`; `__author__` exposto em `__init__.py`.
- Docs: README atualizado para versão 4.1.0 estável.
