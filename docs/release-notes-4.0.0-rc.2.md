# Release notes — 4.0.0-rc.2 (2026-04-16)

## Destaques

Versão candidata a lançamento com foco na **migração do prompt de senha SMTP para interface gráfica**, eliminando qualquer interação via console ao fornecer credenciais SMTP.

## Mudanças

### Prompt de senha SMTP gráfico

- **`src/sentineltray/gui_app.py`** — nova função `prompt_smtp_password_gui(username, monitor_index)`: diálogo modal tkinter com campo de senha mascarado, botões **OK** / **Cancelar**, atalhos `Enter` e `Escape`, centralizado na tela e com o mesmo tema GitHub-dark do restante da interface.
- **`src/sentineltray/entrypoint.py`** — `_prompt_smtp_passwords` reescrita para usar `prompt_smtp_password_gui`; removidas dependências de `getpass` e `input`; cancelar o diálogo encerra o app com `SystemExit`.
- **`src/sentineltray/console_app.py`** — todos os três pontos de uso de `getpass` substituídos por `prompt_smtp_password_gui`; removida importação de `getpass`.

### Testes

- `tests/test_entrypoint_smtp_prompt.py` — mock atualizado para `prompt_smtp_password_gui` em vez de `getpass`.
- `tests/test_console_app.py` — mock atualizado para `prompt_smtp_password_gui` em vez de `getpass`.
