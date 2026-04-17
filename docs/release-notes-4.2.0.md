# Release notes — 4.2.0 (2026-04-17)

## Destaques

Versão **estável** com melhoria no processo de primeiro uso: o arquivo de configuração gerado automaticamente na inicialização agora espelha exatamente o modelo oficial do projeto.

## Novidades nesta versão

- **Config template na primeira inicialização**: quando `config.local.yaml` não existe, o arquivo criado agora copia o conteúdo exato de `config/config.local.yaml.example`, preservando todos os comentários explicativos, valores de exemplo e a estrutura completa da configuração. Anteriormente, era gerado um template genérico embutido em código que diferia do exemplo oficial. O template embutido é mantido como fallback caso o arquivo `.example` não esteja disponível.
