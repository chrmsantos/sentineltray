# Release notes — 3.6.0 (2026-04-15)

## Destaques

- Novo ícone verde em formato de olho para o executável e a bandeja do sistema.
- Documentação completa em português do Brasil no arquivo de configuração de exemplo.

## Mudanças

### Ícone do aplicativo
- **`assets/icon.ico`**: ícone multi-resolução (16, 24, 32, 48, 64, 128, 256 px) gerado com supersampling 4× e filtro LANCZOS para antialiasing suave.
- **`assets/icon_256.png`**: imagem PNG de 256 px para prévia e referência.
- O ícone representa um olho com:
  - Esclera branca recortada em formato de lente/amêndoa.
  - Íris com três camadas de verde (verde-floresta externo → verde-vivo intermediário → verde interno).
  - Pupila escura com reflexo de luz branco.
  - Borda de pálpebra verde-escura e cinco cílios superiores.

### Bandeja do sistema
- **`src/sentineltray/tray_app.py`**: função `_make_green_ball` substituída por `_make_green_eye`, que renderiza o olho descrito acima diretamente via Pillow (sem arquivos externos em tempo de execução).

### Build
- **`SentinelTray.spec`**: parâmetro `icon` adicionado apontando para `assets/icon.ico`; o ícone é agora embutido no `.exe` pelo PyInstaller.

### Configuração
- **`config/config.local.yaml.example`**: todos os campos documentados com comentários detalhados em português do Brasil, organizados em seções: Monitors, Polling & Timing, Arquivos & Logs, Comportamento, Circuit Breaker de Janela, Fila de E-mails e Pausa por Atividade.

### Scripts
- **`scripts/generate_icon.py`**: script standalone para regenerar `assets/icon.ico` e `assets/icon_256.png` a qualquer momento executando `python scripts/generate_icon.py` a partir da raiz do repositório.
