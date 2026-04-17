# Release notes — 4.3.6 (2026-04-17)

## Destaques

Versão **estável** com correção de divergência entre o template embutido e o arquivo de exemplo, garantindo que o `config.local.yaml` gerado automaticamente seja sempre idêntico ao `config.local.yaml.example` do projeto.

## Novidades nesta versão

- **Correção — template de configuração embutido**: o `_CONFIG_TEMPLATE` em `entrypoint.py` foi sincronizado com o conteúdo exato de `config/config.local.yaml.example`. Na situação de fallback (quando o arquivo `.example` não é encontrado em `sys._MEIPASS` nem na raiz do projeto), o arquivo `config.local.yaml` criado automaticamente na primeira execução agora contém o mesmo conteúdo em português, com os mesmos comentários detalhados e valores reais do projeto, em vez do template genérico em inglês com valores placeholder.
