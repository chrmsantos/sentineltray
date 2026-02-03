from __future__ import annotations

import ctypes
import logging
import re
import time
import unicodedata
from typing import Iterable

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementAmbiguousError
    _PYWINAUTO_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - optional dependency
    Desktop = None  # type: ignore[assignment]

    class ElementAmbiguousError(RuntimeError):
        """Fallback error when pywinauto is unavailable."""

    _PYWINAUTO_IMPORT_ERROR = exc

LOGGER = logging.getLogger(__name__)


class WindowUnavailableError(RuntimeError):
    """Raised when the target window is temporarily unavailable or disabled."""


class WindowTextDetector:
    def __init__(
        self,
        window_title_regex: str,
        allow_window_restore: bool = True,
        log_throttle_seconds: int = 60,
    ) -> None:
        self._window_title_regex = re.compile(window_title_regex)
        self._allow_window_restore = allow_window_restore
        self._last_window = None
        self._log_throttle_seconds = max(0, log_throttle_seconds)
        self._last_log: dict[str, float] = {}
        self._phrase_regex_cache: str | None = None
        self._phrase_pattern_cache: re.Pattern[str] | None = None

    @staticmethod
    def _normalize_text(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    def _log_throttled(self, level: int, key: str, message: str, *args: object) -> None:
        if self._log_throttle_seconds == 0:
            LOGGER.log(level, message, *args, extra={"category": "scan"})
            return
        now = time.monotonic()
        last = self._last_log.get(key, 0.0)
        if now - last >= self._log_throttle_seconds:
            self._last_log[key] = now
            LOGGER.log(level, message, *args, extra={"category": "scan"})

    def _window_exists(self, window, timeout: float = 0.0) -> bool:
        try:
            if hasattr(window, "exists") and window.exists(timeout=timeout):
                return True
            if self._window_is_minimized(window):
                return True
            if hasattr(window, "is_visible"):
                return window.is_visible()
            return True
        except Exception:
            return False

    def _window_is_foreground(self, window) -> bool:
        try:
            if hasattr(window, "has_focus") and window.has_focus():
                return True
        except Exception:
            return False
        try:
            if hasattr(window, "is_active") and window.is_active():
                return True
        except Exception:
            return False
        try:
            if hasattr(window, "handle"):
                handle = window.handle
                if handle:
                    return ctypes.windll.user32.GetForegroundWindow() == handle
        except Exception:
            return False
        return False

    def _window_is_maximized(self, window) -> bool:
        try:
            if hasattr(window, "is_maximized"):
                return bool(window.is_maximized())
        except Exception:
            return False
        try:
            if hasattr(window, "handle"):
                handle = window.handle
                if handle:
                    return bool(ctypes.windll.user32.IsZoomed(handle))
        except Exception:
            return False
        return False

    def _window_is_minimized(self, window) -> bool:
        try:
            if hasattr(window, "is_minimized"):
                return bool(window.is_minimized())
        except Exception:
            return False
        try:
            if hasattr(window, "handle"):
                handle = window.handle
                if handle:
                    return bool(ctypes.windll.user32.IsIconic(handle))
        except Exception:
            return False
        return False

    def _force_foreground(self, window) -> None:
        try:
            if hasattr(window, "set_focus"):
                window.set_focus()
        except Exception:
            LOGGER.debug("Failed to set focus", exc_info=True)
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
            user32.SetWindowPos(handle, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            user32.SetWindowPos(handle, -2, 0, 0, 0, 0, 0x0001 | 0x0002)
        except Exception:
            LOGGER.debug("Failed to force window foreground", exc_info=True)

    def _ensure_foreground_and_maximized(self, window) -> None:
        if self._window_is_minimized(window):
            try:
                if hasattr(window, "restore"):
                    window.restore()
            except Exception:
                LOGGER.debug("Failed to restore window", exc_info=True)
            try:
                if hasattr(window, "handle"):
                    handle = window.handle
                    if handle:
                        ctypes.windll.user32.ShowWindow(handle, 9)
            except Exception:
                LOGGER.debug("Failed to restore window via handle", exc_info=True)
        if not self._window_is_foreground(window):
            self._force_foreground(window)
        if not self._window_is_maximized(window):
            try:
                if hasattr(window, "maximize"):
                    window.maximize()
            except Exception:
                LOGGER.debug("Failed to maximize window", exc_info=True)
        if not self._window_is_foreground(window):
            raise WindowUnavailableError("Target window not in foreground")
        if not self._window_is_maximized(window):
            raise WindowUnavailableError("Target window not maximized")

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
        if Desktop is None:
            raise RuntimeError(
                "pywinauto is required for window detection. "
                "Install dependencies from requirements.txt."
            ) from _PYWINAUTO_IMPORT_ERROR
        if self._last_window is not None:
            try:
                if hasattr(self._last_window, "exists"):
                    if self._last_window.exists(timeout=0.5):
                        return self._last_window
                else:
                    return self._last_window
            except Exception:
                self._last_window = None
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
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
            except Exception as exc:
                last_exc = exc
                self._log_throttled(
                    logging.WARNING,
                    "window_lookup_failed",
                    "Window lookup failed (attempt %s/3): %s",
                    attempt + 1,
                    exc,
                )
                time.sleep(0.5 * (2**attempt))
        raise WindowUnavailableError("Target window lookup failed") from last_exc

    def check_ready(self) -> None:
        window = self._get_window()
        if not self._window_exists(window, timeout=1.0):
            raise WindowUnavailableError("Target window not found")
        self._ensure_foreground_and_maximized(window)

    def _iter_texts(self) -> Iterable[str]:
        window = self._get_window()
        if not self._window_exists(window, timeout=1.0):
            raise WindowUnavailableError("Target window not found")
        self._ensure_foreground_and_maximized(window)

        texts: list[str] = []
        try:
            try:
                if hasattr(window, "window_text"):
                    title_text = window.window_text()
                    if title_text:
                        texts.append(title_text)
            except Exception:
                LOGGER.debug("Failed to read window title text", exc_info=True)
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

        phrase_value = "" if phrase_regex is None else str(phrase_regex)
        if not phrase_value.strip():
            return texts

        normalized_regex = self._normalize_text(phrase_value)
        if normalized_regex != self._phrase_regex_cache or self._phrase_pattern_cache is None:
            try:
                pattern = re.compile(normalized_regex, re.IGNORECASE)
            except re.error as exc:
                raise ValueError("Invalid phrase regex") from exc
            self._phrase_regex_cache = normalized_regex
            self._phrase_pattern_cache = pattern
        pattern = self._phrase_pattern_cache
        matches: list[str] = []
        normalize = self._normalize_text
        for text in texts:
            if pattern.search(normalize(text)):
                matches.append(text)
        return matches
