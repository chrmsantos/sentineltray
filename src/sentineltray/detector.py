from __future__ import annotations

import ctypes
import logging
import re
import time
import unicodedata
from typing import Iterable

from pywinauto import Desktop
from pywinauto.findwindows import ElementAmbiguousError

LOGGER = logging.getLogger(__name__)


class WindowUnavailableError(RuntimeError):
    """Raised when the target window is temporarily unavailable or disabled."""


class WindowTextDetector:
    def __init__(self, window_title_regex: str, allow_window_restore: bool = True) -> None:
        self._window_title_regex = re.compile(window_title_regex)
        self._allow_window_restore = allow_window_restore
        self._last_window = None

    def _window_exists(self, window, timeout: float = 0.0) -> bool:
        try:
            if hasattr(window, "exists") and window.exists(timeout=timeout):
                return True
            if hasattr(window, "is_minimized") and window.is_minimized():
                return True
            if hasattr(window, "is_visible"):
                return window.is_visible()
            return True
        except Exception:
            return False

    def _select_best_window(self, desktop: Desktop):
        candidates = desktop.windows(title_re=self._window_title_regex)
        if not candidates:
            raise ElementAmbiguousError("No window candidates available")

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
            "Multiple windows matched; selecting best candidate (%s found)",
            len(candidates),
            extra={"category": "scan"},
        )
        return selected

    def _get_window(self):
        if self._last_window is not None:
            try:
                if hasattr(self._last_window, "exists"):
                    if self._last_window.exists(timeout=0.5):
                        return self._last_window
                else:
                    return self._last_window
            except Exception:
                self._last_window = None
        desktop = Desktop(backend="uia")
        try:
            window_spec = desktop.window(title_re=self._window_title_regex)
        except ElementAmbiguousError:
            return self._select_best_window(desktop)

        try:
            window = window_spec.wrapper_object()
            self._last_window = window
            return window
        except ElementAmbiguousError:
            window = self._select_best_window(desktop)
            self._last_window = window
            return window
        except Exception:
            self._last_window = window_spec
            return window_spec

    def _prepare_window(self, window) -> None:
        try:
            if hasattr(window, "is_minimized") and window.is_minimized():
                window.restore()
            if hasattr(window, "is_maximized") and not window.is_maximized():
                if hasattr(window, "maximize"):
                    window.maximize()
            if hasattr(window, "set_focus"):
                window.set_focus()
            self._force_foreground(window)
        except Exception as exc:
            raise WindowUnavailableError("Target window could not be restored") from exc

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
                    self._force_foreground(window)
                except Exception:
                    LOGGER.debug("Window restore retry failed", exc_info=True)
                time.sleep(0.5)
                try:
                    window = self._get_window()
                except Exception:
                    continue
        raise WindowUnavailableError("Target window not visible") from last_exc

    def _minimize_window(self, window) -> None:
        if not self._allow_window_restore:
            return
        try:
            if hasattr(window, "minimize"):
                window.minimize()
        except Exception:
            LOGGER.debug("Failed to minimize target window", exc_info=True)

    def _force_foreground(self, window) -> None:
        try:
            if not hasattr(window, "handle"):
                return
            handle = window.handle
            if not handle:
                return
            user32 = ctypes.windll.user32
            user32.ShowWindow(handle, 3)
            user32.BringWindowToTop(handle)
            user32.SetForegroundWindow(handle)
        except Exception:
            LOGGER.debug("Failed to force window foreground", exc_info=True)

    def _iter_texts(self) -> Iterable[str]:
        window = self._get_window()
        self._minimize_all_windows(exclude=window)
        retry_delays = (1.0, 2.0, 4.0)
        if not self._window_exists(window, timeout=2):
            for delay in retry_delays:
                LOGGER.info("Target window not found, retrying", extra={"category": "scan"})
                time.sleep(delay)
                window = self._get_window()
                if self._window_exists(window, timeout=2):
                    break
            else:
                raise WindowUnavailableError("Target window not found")

        self._prepare_window(window)

        try:
            if hasattr(window, "is_enabled") and not window.is_enabled():
                raise WindowUnavailableError("Target window not enabled")
        except Exception as exc:
            raise WindowUnavailableError("Target window not enabled") from exc

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

    def _minimize_all_windows(self, exclude=None) -> None:
        try:
            exclude_handle = None
            if exclude is not None and hasattr(exclude, "handle"):
                exclude_handle = exclude.handle
            desktop = Desktop(backend="uia")
            for item in desktop.windows():
                try:
                    if exclude_handle and hasattr(item, "handle") and item.handle == exclude_handle:
                        continue
                    if hasattr(item, "minimize"):
                        item.minimize()
                except Exception:
                    LOGGER.debug("Failed to minimize window", exc_info=True)
        except Exception:
            LOGGER.debug("Failed to enumerate windows for minimize", exc_info=True)

    def find_matches(self, phrase_regex: str) -> list[str]:
        texts = self._iter_texts()
        if not texts:
            return []

        if not phrase_regex:
            return texts

        def normalize(value: str) -> str:
            decomposed = unicodedata.normalize("NFKD", value)
            return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

        normalized_regex = normalize(phrase_regex)
        pattern = re.compile(normalized_regex, re.IGNORECASE)
        matches: list[str] = []
        for text in texts:
            if pattern.search(normalize(text)):
                matches.append(text)
        return matches
