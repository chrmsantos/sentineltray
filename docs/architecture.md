# Architecture

## Overview

- Window text detection uses UI Automation via pywinauto.
- WhatsApp delivery supports two modes:
  - web: WhatsApp Web via Playwright with persistent session
  - cloud_api: WhatsApp Cloud API via HTTPS
- State is stored in state.json to prevent duplicate sends.
- Logs rotate with a max of 5 files.
- System tray UI shows status and controls exit.
- Tray icon is rendered via Pillow with fixed-size rectangle glyphs.
- Cloud API send tests use mocked HTTP calls to avoid external traffic.
- Local override config can be loaded from %LOCALAPPDATA%\SentinelTray\config.local.yaml.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.
