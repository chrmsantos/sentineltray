from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from .config import AppConfig
from .detector import WindowTextDetector
from .logging_setup import setup_logging
from .status import StatusStore
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


@dataclass
class Notifier:
    config: AppConfig
    status: StatusStore

    def __post_init__(self) -> None:
        self._detector = WindowTextDetector(self.config.window_title_regex)
        self._sender = build_sender(self.config.whatsapp)
        self._state_path = Path(self.config.state_file)
        self._history = _load_state(self._state_path)

    def scan_once(self) -> None:
        self.status.set_last_scan(_now_iso())
        matches = self._detector.find_matches(self.config.phrase_regex)
        normalized = [_normalize(text) for text in matches if text]
        new_items = [text for text in normalized if text not in self._history]

        if new_items:
            self.status.set_last_match(new_items[0])

        for text in new_items:
            self._sender.send(text)
            self.status.set_last_send(_now_iso())
            LOGGER.info("Sent message")
            self._history.append(text)

        if len(self._history) > self.config.max_history:
            self._history = self._history[-self.config.max_history :]
            _save_state(self._state_path, self._history)
        elif new_items:
            _save_state(self._state_path, self._history)

    def run_loop(self, stop_event: Event) -> None:
        setup_logging(self.config.log_file)
        LOGGER.info("SentinelTray started")
        self.status.set_running(True)

        while not stop_event.is_set():
            try:
                self.scan_once()
            except Exception as exc:
                self.status.set_last_error(str(exc))
                LOGGER.exception("Loop error: %s", exc)

            stop_event.wait(self.config.poll_interval_seconds)

        self.status.set_running(False)


def run(config: AppConfig) -> None:
    status = StatusStore()
    notifier = Notifier(config=config, status=status)
    stop_event = Event()
    notifier.run_loop(stop_event)
