from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pywinauto import Desktop
from pywinauto.findwindows import ElementAmbiguousError
from pywinauto.keyboard import send_keys

from .config import WhatsAppConfig

LOGGER = logging.getLogger(__name__)

LOGIN_PROMPTS = (
    "Use WhatsApp on your phone",
    "Use o WhatsApp no seu telefone",
    "Escaneie o código QR",
    "Scan the QR code",
    "QR code",
)

SEARCH_SHORTCUTS = ("^n", "^k")


class WhatsAppError(RuntimeError):
    """Base WhatsApp error."""


class WhatsAppUnavailableError(WhatsAppError):
    """Raised when WhatsApp is not available or not running."""


class WhatsAppNotLoggedInError(WhatsAppError):
    """Raised when WhatsApp is open but not logged in."""


class WhatsAppContactNotFoundError(WhatsAppError):
    """Raised when WhatsApp contact/group cannot be selected."""


class WhatsAppSendError(WhatsAppError):
    """Raised when a WhatsApp message could not be sent."""


@dataclass
class WhatsAppSender:
    config: WhatsAppConfig
    log_throttle_seconds: int = 60
    _last_log: dict[str, float] = field(default_factory=dict)

    def _log_throttled(self, level: int, key: str, message: str, *args: object) -> None:
        now = time.monotonic()
        last = self._last_log.get(key, 0.0)
        if (now - last) < max(0, self.log_throttle_seconds):
            return
        self._last_log[key] = now
        LOGGER.log(level, message, *args, extra={"category": "whatsapp"})

    def _select_best_window(self, desktop: Desktop, title_re: str):
        candidates = desktop.windows(title_re=title_re)
        if not candidates:
            raise WhatsAppUnavailableError("WhatsApp window not found")

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
        return selected

    def _get_window(self):
        title_re = self.config.window_title_regex or "WhatsApp"
        desktop = Desktop(backend="uia")
        try:
            window_spec = desktop.window(title_re=title_re)
        except ElementAmbiguousError:
            return self._select_best_window(desktop, title_re)

        try:
            window = window_spec.wrapper_object()
            return window
        except ElementAmbiguousError:
            return self._select_best_window(desktop, title_re)
        except Exception as exc:
            raise WhatsAppUnavailableError("WhatsApp window not available") from exc

    def _ensure_foreground(self, window) -> None:
        try:
            if hasattr(window, "is_minimized") and window.is_minimized():
                if hasattr(window, "restore"):
                    window.restore()
            if hasattr(window, "set_focus"):
                window.set_focus()
            if hasattr(window, "handle"):
                handle = window.handle
                if handle:
                    user32 = __import__("ctypes").windll.user32
                    user32.ShowWindow(handle, 3)
                    user32.BringWindowToTop(handle)
                    user32.SetForegroundWindow(handle)
        except Exception as exc:
            raise WhatsAppUnavailableError("Failed to focus WhatsApp window") from exc

    def _check_logged_in(self, window) -> None:
        try:
            for item in window.descendants():
                try:
                    text = (item.window_text() or "").strip()
                except Exception:
                    continue
                if not text:
                    continue
                for prompt in LOGIN_PROMPTS:
                    if prompt.lower() in text.lower():
                        raise WhatsAppNotLoggedInError("WhatsApp not logged in")
        except WhatsAppNotLoggedInError:
            raise
        except Exception:
            self._log_throttled(
                logging.WARNING,
                "login_check_failed",
                "WhatsApp login status could not be verified",
            )

    def _open_chat(self, contact_name: str) -> None:
        for shortcut in SEARCH_SHORTCUTS:
            try:
                send_keys(shortcut, pause=0.02)
                time.sleep(0.2)
                send_keys(contact_name, with_spaces=True, pause=0.02, vk_packet=True)
                time.sleep(0.4)
                send_keys("{ENTER}")
                return
            except Exception:
                continue
        raise WhatsAppContactNotFoundError("Failed to open contact search")

    def _send_message(self, message: str) -> None:
        try:
            send_keys(message, with_spaces=True, pause=0.02, vk_packet=True)
            send_keys("{ENTER}")
        except Exception as exc:
            raise WhatsAppSendError("Failed to send WhatsApp message") from exc

    def send(self, message: str) -> None:
        if not self.config.enabled:
            LOGGER.info("WhatsApp disabled; skipping send", extra={"category": "whatsapp"})
            return
        if not self.config.contact_name:
            raise ValueError("whatsapp.contact_name is required")
        if not message:
            raise ValueError("WhatsApp message is empty")

        attempts = max(0, self.config.retry_attempts)
        backoff = max(0, self.config.retry_backoff_seconds)

        for attempt in range(attempts + 1):
            try:
                window = self._get_window()
                self._ensure_foreground(window)
                self._check_logged_in(window)
                self._open_chat(self.config.contact_name)
                self._send_message(message)
                LOGGER.info("WhatsApp message sent", extra={"category": "whatsapp"})
                return
            except WhatsAppNotLoggedInError as exc:
                self._log_throttled(logging.ERROR, "not_logged_in", "%s", exc)
                raise
            except WhatsAppContactNotFoundError as exc:
                self._log_throttled(logging.ERROR, "contact_not_found", "%s", exc)
                raise
            except WhatsAppUnavailableError as exc:
                self._log_throttled(logging.ERROR, "unavailable", "%s", exc)
                raise
            except WhatsAppSendError as exc:
                self._log_throttled(logging.ERROR, "send_failed", "%s", exc)
                if attempt >= attempts:
                    raise
                if backoff:
                    time.sleep(backoff * (2**attempt))
            except Exception as exc:
                self._log_throttled(logging.ERROR, "unexpected", "%s", exc)
                if attempt >= attempts:
                    raise WhatsAppSendError("Unexpected WhatsApp failure") from exc
                if backoff:
                    time.sleep(backoff * (2**attempt))

    def check_ready(self) -> None:
        if not self.config.enabled:
            return
        if not self.config.contact_name:
            raise ValueError("whatsapp.contact_name is required")
        window = self._get_window()
        self._ensure_foreground(window)
        self._check_logged_in(window)


def build_message_template(template: str, *, message: str, window: str) -> str:
    text = (template or "").strip()
    if not text:
        return message
    now = datetime.now(timezone.utc).isoformat()
    value = text
    value = value.replace("{message}", message)
    value = value.replace("{match}", message)
    value = value.replace("{window}", window)
    value = value.replace("{timestamp}", now)
    return value
