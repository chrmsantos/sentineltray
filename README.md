# SentinelTray

Minimal Windows notifier that reads visible text from a target desktop app and sends a WhatsApp message when a phrase appears.

## Requirements

- Windows user session (no admin required).
- Python 3.11+.
- WhatsApp Web login for web mode.
- Python 3.14 uses PyYAML 6.0.3.

## Setup

1. Create a virtual environment and install dependencies:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Install Playwright browsers once:

   python -m playwright install

3. Edit config.yaml and set:

- window_title_regex
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- whatsapp.mode
- whatsapp.chat_target
- whatsapp.chat_target must match the chat name shown in WhatsApp Web
- whatsapp.dry_run = false when ready to send

Sensitive settings (like window_title_regex and chat_target) can be stored in a local file:

- %USERPROFILE%\sentineltray\config.local.yaml

This local file overrides config.yaml. You can also set SENTINELTRAY_CONFIG to
point to a local config file.

If config.local.yaml is missing, empty, or invalid, the app creates it,
opens it for editing, and exits so you can fill it.

## Run

python main.py

The app runs in the system tray by default. Use the tray menu to open Status.

CLI mode (no tray):

python main.py --cli

## Notes

- Logs are written per execution with detailed fields and kept with a max of 5 files in logs/.
- Third-party debug logs are suppressed to keep logs actionable.
- state.json stores the last sent messages to avoid duplicates.
- Runtime artifacts are ignored by git via .gitignore.
- License: GPL-3.0-only.
