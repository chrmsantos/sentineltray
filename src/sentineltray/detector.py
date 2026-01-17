from __future__ import annotations

import logging
import re
import time
from typing import Iterable

from pywinauto import Desktop

LOGGER = logging.getLogger(__name__)


class WindowTextDetector:
    def __init__(self, window_title_regex: str, allow_window_restore: bool = True) -> None:
        self._window_title_regex = re.compile(window_title_regex)
        self._allow_window_restore = allow_window_restore

    def _get_window(self):
        desktop = Desktop(backend="uia")
        return desktop.window(title_re=self._window_title_regex)

    def _prepare_window(self, window) -> None:
        try:
            if self._allow_window_restore:
                if hasattr(window, "is_minimized") and window.is_minimized():
                    window.restore()
                if hasattr(window, "is_maximized") and not window.is_maximized():
                    if hasattr(window, "maximize"):
                        window.maximize()
                if hasattr(window, "set_focus"):
                    window.set_focus()
        except Exception as exc:
            raise RuntimeError("Target window could not be restored") from exc

        try:
            window.wait("visible", timeout=2)
        except Exception:
            try:
                if hasattr(window, "restore"):
                    window.restore()
                window.wait("visible", timeout=2)
            except Exception as exc:
                raise RuntimeError("Target window not visible") from exc

    def _minimize_window(self, window) -> None:
        if not self._allow_window_restore:
            return
        try:
            if hasattr(window, "minimize"):
                window.minimize()
        except Exception:
            LOGGER.debug("Failed to minimize target window", exc_info=True)

    def _iter_texts(self) -> Iterable[str]:
        window = self._get_window()
        if not window.exists(timeout=2):
            LOGGER.info("Target window not found, retrying", extra={"category": "scan"})
            time.sleep(1)
            window = self._get_window()
            if not window.exists(timeout=2):
                raise RuntimeError("Target window not found")

        self._prepare_window(window)

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
        finally:
            self._minimize_window(window)

        return texts

    def find_matches(self, phrase_regex: str) -> list[str]:
        texts = self._iter_texts()
        if not texts:
            return []

        if not phrase_regex:
            return texts

        pattern = re.compile(phrase_regex)
        return [text for text in texts if pattern.search(text)]
