# Architecture

## Overview

- Window text detection uses UI Automation via pywinauto.
- WhatsApp delivery uses WhatsApp Web via Playwright with persistent session.
- State is stored in state.json to prevent duplicate sends.
- Logs are created per execution with detailed fields and kept with a max of 5 files.
- Third-party debug log noise is suppressed at the logger level.
- System tray UI shows status and controls exit.
- Errors in each polling iteration are reported on screen and via WhatsApp.
- A startup test message is sent via WhatsApp on each run to confirm delivery.
- Periodic healthchecks send uptime and last activity via WhatsApp.
- Tray icon is rendered via Pillow with fixed-size rectangle glyphs.
- Local override config can be loaded from %USERPROFILE%\sentineltray\config.local.yaml.
- Missing, empty, or invalid local override triggers file creation and edit prompt.
- Local file templates live under templates/local/.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.
