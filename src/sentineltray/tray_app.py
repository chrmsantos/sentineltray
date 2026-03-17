from __future__ import annotations

import ctypes
import logging
import threading
from typing import Callable

import pystray  # type: ignore[import]
from PIL import Image, ImageDraw  # type: ignore[import]

LOGGER = logging.getLogger(__name__)

_SW_HIDE = 0
_SW_SHOW = 5


def _make_green_ball(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    # Light green fill with a slightly darker green outline for definition
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill="#90EE90",
        outline="#4CAF50",
        width=2,
    )
    return img


def _console_hwnd() -> int:
    try:
        return int(ctypes.windll.kernel32.GetConsoleWindow())  # type: ignore[attr-defined]
    except Exception:
        return 0


def _set_console_visible(visible: bool) -> None:
    hwnd = _console_hwnd()
    if not hwnd:
        return
    try:
        ctypes.windll.user32.ShowWindow(hwnd, _SW_SHOW if visible else _SW_HIDE)  # type: ignore[attr-defined]
    except Exception:
        pass


class TrayIcon:
    """System-tray icon with a green ball that shows/hides the console window."""

    def __init__(self, *, on_exit_requested: Callable[[], None]) -> None:
        self._on_exit_requested = on_exit_requested
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None
        self._console_visible = False

    # ------------------------------------------------------------------
    # Menu callbacks (called from the pystray thread)
    # ------------------------------------------------------------------

    def _console_menu_label(self, item: pystray.MenuItem) -> str:
        return "Fechar Console" if self._console_visible else "Abrir Console"

    def _toggle_console(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._console_visible = not self._console_visible
        _set_console_visible(self._console_visible)
        icon.update_menu()

    def _on_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        icon.stop()
        self._on_exit_requested()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Hide the console window and show the tray icon."""
        _set_console_visible(False)
        self._console_visible = False

        menu = pystray.Menu(
            pystray.MenuItem(self._console_menu_label, self._toggle_console),
            pystray.MenuItem("Sair", self._on_exit),
        )
        self._icon = pystray.Icon(
            "SentinelTray",
            _make_green_ball(),
            "SentinelTray",
            menu,
        )
        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="tray-icon",
        )
        self._thread.start()
        LOGGER.info("Tray icon started", extra={"category": "startup"})

    def stop(self) -> None:
        """Stop the tray icon and restore the console window."""
        if self._icon is not None:
            _set_console_visible(True)
            try:
                self._icon.stop()
            except Exception as exc:
                LOGGER.debug("Tray icon stop error: %s", exc, extra={"category": "startup"})
            self._icon = None
