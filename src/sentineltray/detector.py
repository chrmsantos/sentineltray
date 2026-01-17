from __future__ import annotations

import logging
import re
import time
from typing import Iterable

from pywinauto import Desktop
from pywinauto.findwindows import ElementAmbiguousError

LOGGER = logging.getLogger(__name__)


class WindowTextDetector:
    def __init__(self, window_title_regex: str, allow_window_restore: bool = True) -> None:
        self._window_title_regex = re.compile(window_title_regex)
        self._allow_window_restore = allow_window_restore

    def _get_window(self):
        desktop = Desktop(backend="uia")
        try:
            return desktop.window(title_re=self._window_title_regex)
        except ElementAmbiguousError:
            candidates = desktop.windows(title_re=self._window_title_regex)
            if not candidates:
                raise

            def score(window) -> int:
                value = 0
                try:
                    if hasattr(window, "has_focus") and window.has_focus():
                        value += 3
                except Exception:
                    pass
                try:
                    if hasattr(window, "is_visible") and window.is_visible():
                        value += 2
                except Exception:
                    pass
                try:
                    if hasattr(window, "is_enabled") and window.is_enabled():
                        value += 1
                except Exception:
                    pass
                return value

            selected = sorted(candidates, key=score, reverse=True)[0]
            LOGGER.info(
                "Multiple windows matched; selecting best candidate",
                extra={"category": "scan"},
            )
            return selected

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

        last_exc: Exception | None = None
        timeouts = (2, 3, 4)
        for timeout in timeouts:
            try:
                window.wait("visible", timeout=timeout)
                return
            except Exception as exc:
                last_exc = exc
                LOGGER.info(
                    "Target window not visible (retrying)",
                    extra={"category": "scan"},
                )
                try:
                    if hasattr(window, "restore"):
                        window.restore()
                    if hasattr(window, "set_focus"):
                        window.set_focus()
                    if hasattr(window, "is_maximized") and not window.is_maximized():
                        if hasattr(window, "maximize"):
                            window.maximize()
                except Exception:
                    LOGGER.debug("Window restore retry failed", exc_info=True)
                time.sleep(0.5)
                try:
                    window = self._get_window()
                except Exception:
                    continue
        raise RuntimeError("Target window not visible") from last_exc

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
