# Architecture

## Overview

- Window text detection uses UI Automation via pywinauto.
- WhatsApp delivery supports two modes:
  - web: WhatsApp Web via Playwright with persistent session
  - cloud_api: WhatsApp Cloud API via HTTPS
- State is stored in state.json to prevent duplicate sends.
- Logs rotate with a max of 5 files.

## Data Flow

1. Poll target window every N seconds.
2. Extract visible texts.
3. Filter by phrase regex.
4. Send new matches.
