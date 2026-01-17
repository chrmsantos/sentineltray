from __future__ import annotations

import logging
import re
from typing import Iterable

from pywinauto import Desktop

LOGGER = logging.getLogger(__name__)


class WindowTextDetector:
    def __init__(self, window_title_regex: str) -> None:
        self._window_title_regex = re.compile(window_title_regex)

    def _get_window(self):
        desktop = Desktop(backend="uia")
        return desktop.window(title_re=self._window_title_regex)

    def _iter_texts(self) -> Iterable[str]:
        window = self._get_window()
        if not window.exists(timeout=2):
            raise RuntimeError("Target window not found")

        try:
            window.wait("visible", timeout=2)
        except Exception as exc:
            raise RuntimeError("Target window not visible") from exc

        try:
            if hasattr(window, "is_enabled") and not window.is_enabled():
                raise RuntimeError("Target window not enabled")
        except Exception as exc:
            raise RuntimeError("Target window not enabled") from exc

        texts: list[str] = []
        try:
            for element in window.descendants():
                try:
                    text = element.window_text()
                except Exception:
                    continue
                if text:
                    texts.append(text)
        except Exception as exc:
            raise RuntimeError("Failed to read window texts") from exc

        return texts

    def find_matches(self, phrase_regex: str) -> list[str]:
        texts = self._iter_texts()
        if not texts:
            return []

        if not phrase_regex:
            return texts

        pattern = re.compile(phrase_regex)
        return [text for text in texts if pattern.search(text)]
