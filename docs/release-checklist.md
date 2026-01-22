# Release Checklist

## Pre-release
- [ ] Changelog atualizado
- [ ] Versão/label atualizados
- [ ] Revisão de privacidade (PRIVACY.md)
- [ ] Revisão de segurança (SECURITY.md)
- [ ] Sem segredos no repositório

## CI/Automação
- [ ] CodeQL passou
- [ ] pip-audit passou
- [ ] bandit passou
- [ ] Scorecard sem falhas críticas

## Release artifacts
- [ ] SBOM anexado
- [ ] Relatórios pip-audit e bandit anexados
- [ ] Provenance (SLSA) anexado

## Pós-release
- [ ] Verificar release assets no GitHub
- [ ] Comunicar mudanças relevantes
