from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .config import AppConfig
from .detector import WindowTextDetector
from .logging_setup import setup_logging
from .whatsapp_sender import build_sender

LOGGER = logging.getLogger(__name__)


def _load_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        return []
    return []


def _save_state(path: Path, items: list[str]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join(text.split())


def run(config: AppConfig) -> None:
    setup_logging(config.log_file)
    LOGGER.info("Notifier started")

    detector = WindowTextDetector(config.window_title_regex)
    sender = build_sender(config.whatsapp)

    state_path = Path(config.state_file)
    history = _load_state(state_path)

    while True:
        try:
            matches = detector.find_matches(config.phrase_regex)
            normalized = [_normalize(text) for text in matches if text]
            new_items = [text for text in normalized if text not in history]

            for text in new_items:
                sender.send(text)
                LOGGER.info("Sent message")
                history.append(text)

            if len(history) > config.max_history:
                history = history[-config.max_history :]
                _save_state(state_path, history)
            elif new_items:
                _save_state(state_path, history)
        except Exception as exc:
            LOGGER.exception("Loop error: %s", exc)

        time.sleep(config.poll_interval_seconds)
