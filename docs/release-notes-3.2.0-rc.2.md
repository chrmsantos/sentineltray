# Release notes — 3.2.0-rc.2 (2026-04-09)

## Highlights

- O app agora inicia sempre minimizado na bandeja do sistema, sem exibir a janela do console.
- Clicar em fechar (×) na janela do console minimiza para a bandeja ao invés de encerrar o processo.

## Mudanças

- **Iniciar minimizado**: `run_console()` oculta o console como primeira ação, antes mesmo de criar qualquer objeto, eliminando qualquer flash da janela na inicialização.
- **Fechar para bandeja**: `SetConsoleCtrlHandler` intercepta o evento `CTRL_CLOSE_EVENT` (botão × da janela do console) e esconde o console ao invés de encerrar o processo. O ícone na bandeja permanece ativo.
- O handler de fechamento é deregistrado automaticamente ao sair via "Sair" no menu da bandeja.
