# Notificator

Minimal Windows notifier that reads visible text from a target desktop app and sends a WhatsApp message when a phrase appears.

## Requirements

- Windows user session (no admin required).
- Python 3.11+.
- WhatsApp Web login for web mode, or WhatsApp Cloud API credentials for cloud_api mode.
- Python 3.14 uses PyYAML 6.0.3.

## Setup

1. Create a virtual environment and install dependencies:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. If using web mode, install Playwright browsers once:

   python -m playwright install

3. Edit config.yaml and set:

- window_title_regex
- phrase_regex (empty means any visible text)
- use single quotes for regex to avoid YAML escape issues
- whatsapp.mode
- whatsapp.chat_target or whatsapp.cloud_api
- whatsapp.chat_target must match the chat name shown in WhatsApp Web
- whatsapp.dry_run = false when ready to send

## Run

python main.py

## Notes

- Logs are kept with a max of 5 files in logs/.
- state.json stores the last sent messages to avoid duplicates.
