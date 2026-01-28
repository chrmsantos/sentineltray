from __future__ import annotations

import ctypes
from ctypes import wintypes
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
            if hasattr(window, "is_minimized") and window.is_minimized():
                return True
            if hasattr(window, "is_visible"):
                return window.is_visible()
            return True
        except Exception:
            return False

    def _window_has_area(self, window) -> bool:
        try:
            if hasattr(window, "rectangle"):
                rect = window.rectangle()
                return rect.width() > 0 and rect.height() > 0
        except Exception:
            return False
        return False

    def _window_is_visible(self, window) -> bool:
        try:
            if hasattr(window, "is_visible"):
                return bool(window.is_visible())
        except Exception:
            return False
        return False

    def _window_is_enabled(self, window) -> bool:
        try:
            if hasattr(window, "is_enabled"):
                return bool(window.is_enabled())
        except Exception:
            return False
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

    def check_ready(self) -> None:
        window = self._get_window()
        if not self._window_exists(window, timeout=1.0):
            raise WindowUnavailableError("Target window not found")
        if not self._window_has_area(window):
            raise WindowUnavailableError("Target window has no visible area")
        if not self._window_is_enabled(window):
            raise WindowUnavailableError("Target window not enabled")

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
            self._click_title_bar(window)
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
                self._log_throttled(
                    logging.INFO,
                    "window_not_visible",
                    "Target window not visible (retrying)",
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
                    self._click_title_bar(window)
                except Exception:
                    LOGGER.debug("Window restore retry failed", exc_info=True)
                time.sleep(0.5)
                try:
                    window = self._get_window()
                except Exception:
                    continue
        exists = self._window_exists(window, timeout=0.0)
        has_area = self._window_has_area(window)
        is_visible = self._window_is_visible(window)
        is_enabled = self._window_is_enabled(window)
        if exists and has_area:
            if is_visible and is_enabled:
                LOGGER.info(
                    "Visibility wait timed out; window reports visible and enabled; proceeding",
                    extra={"category": "scan"},
                )
            else:
                LOGGER.warning(
                    "Target window visibility check failed; proceeding with scan (visible=%s enabled=%s)",
                    is_visible,
                    is_enabled,
                    extra={"category": "scan"},
                )
            return
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
            user32.SetWindowPos(handle, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            user32.SetWindowPos(handle, -2, 0, 0, 0, 0, 0x0001 | 0x0002)
        except Exception:
            LOGGER.debug("Failed to force window foreground", exc_info=True)

    def _click_title_bar(self, window) -> None:
        try:
            if not hasattr(window, "rectangle"):
                return
            rect = window.rectangle()
            if not rect:
                return
            width = rect.width()
            height = rect.height()
            if width <= 0 or height <= 0:
                return
            x = rect.left + max(5, width // 2)
            y = rect.top + 10
            user32 = ctypes.windll.user32
            point = wintypes.POINT()
            if user32.GetCursorPos(ctypes.byref(point)) == 0:
                return
            user32.SetCursorPos(int(x), int(y))
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            user32.SetCursorPos(point.x, point.y)
        except Exception:
            LOGGER.debug("Failed to click title bar", exc_info=True)

    def _iter_texts(self) -> Iterable[str]:
        window = self._get_window()
        if self._allow_window_restore:
            self._minimize_all_windows(exclude=window)
        retry_delays = (1.0, 2.0, 4.0)
        if not self._window_exists(window, timeout=2):
            for delay in retry_delays:
                self._log_throttled(
                    logging.INFO,
                    "window_not_found",
                    "Target window not found, retrying",
                )
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
