# Auditoria e Controles

Este documento consolida os controles técnicos usados para apoiar auditorias de procedência, segurança e privacidade.

## Automação por release

- SBOM (SPDX) anexado em releases.
- Relatórios de vulnerabilidade (pip-audit) anexados em releases.
- Relatórios de segurança estática (bandit) anexados em releases.
- Provenance (SLSA) anexado em releases.

## Verificações contínuas

- CodeQL em push/PR.
- Dependabot semanal.
- OpenSSF Scorecard semanal.
- mypy para verificação de tipagem.

## Logs e minimização

- Redação de e-mails, telefones e paths locais em logs e exportações.
- Telemetria e status exportados apenas localmente.
- Históricos reduzidos e com hash.

## Retenção

- Logs limitados por quantidade e tamanho.
- Filas de envio com limites de idade e tentativas.

## Contato

- Reporte de vulnerabilidades: ver SECURITY.md
- Política de privacidade: ver PRIVACY.md
