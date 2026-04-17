# Release notes — 4.1.0 (2026-04-17)

## Destaques

Primeira versão **estável** da linha 4.x. Consolida todas as funcionalidades das versões 3.x e os dois release candidates 4.0.0-rc.1 e 4.0.0-rc.2.

## Novidades nesta versão

- **GUI — janela aberta ao iniciar**: o app abre com a janela de status visível na inicialização, em vez de iniciar minimizado somente na bandeja do sistema.
- **GUI — autor no rodapé**: nome do autor *Christian Martin dos Santos* exibido no rodapé da janela de status.
- **Metadados**: campo `authors` adicionado ao `pyproject.toml`; constante `__author__` exposta em `sentineltray/__init__.py`.

## Funcionalidades acumuladas desde 3.0.0

### Interface gráfica (4.0.0-rc.1 / 4.0.0-rc.2)
- Janela de status completa com tema GitHub-dark substituindo a interface de console.
- Layout de duas colunas (1080×580, redimensionável, mínimo 900×480).
- Editor de configuração YAML integrado — sem dependência do Bloco de Notas.
- Validação em tempo real do YAML antes de salvar; aplicação imediata sem reiniciar.
- Prompt de senha SMTP em diálogo gráfico tkinter (sem uso de `getpass`).
- Ícone de bandeja verde em formato de olho com ação padrão "Abrir Status".

### Monitoramento
- Scan não intrusivo: janela restaurada ao estado original após a leitura.
- Múltiplos monitores suportados simultaneamente.
- Alertas com delta numérico (+N/-N) nas mensagens enviadas.
- Scan contínuo, independente da atividade do usuário.

### Confiabilidade
- Circuit breaker e backoff exponencial por monitor.
- Fila local de e-mails com reenvio automático em caso de falha de entrega.
- Watchdog detecta threads mortas e reinicia o notifier automaticamente.
- Instâncias duplicadas encerradas automaticamente ao iniciar.

### Segurança e privacidade
- Senhas SMTP armazenadas via Windows DPAPI (nunca em texto simples).
- Logs redactam e-mails e caminhos locais; hashes para resumos de correspondências.
- Dados sensíveis isolados em `%LOCALAPPDATA%\ZWave\Tmp\SentinelTray\Config`.

### Outros
- Interface totalmente em português do Brasil.
- Flags `--version` e `--help` na linha de comando.
- Executável `SentinelTray.exe` sem console (sem flash ao iniciar).
