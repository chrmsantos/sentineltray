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


def set_console_visible(visible: bool) -> None:
    hwnd = _console_hwnd()
    if not hwnd:
        return
    try:
        ctypes.windll.user32.ShowWindow(hwnd, _SW_SHOW if visible else _SW_HIDE)  # type: ignore[attr-defined]
    except Exception:
        pass


_CTRL_CLOSE_EVENT = 2
_HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)  # type: ignore[attr-defined]


def _install_close_to_tray_handler(tray: "TrayIcon") -> object:
    """Register a SetConsoleCtrlHandler that hides the console on [X] instead of terminating."""

    @_HandlerRoutine
    def _handler(ctrl_type: int) -> bool:
        if ctrl_type == _CTRL_CLOSE_EVENT:
            tray._console_visible = False
            set_console_visible(False)
            if tray._icon is not None:
                try:
                    tray._icon.update_menu()
                except Exception:
                    pass
            return True  # suppress default close / terminate
        return False

    try:
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler, True)  # type: ignore[attr-defined]
    except Exception as exc:
        LOGGER.debug("SetConsoleCtrlHandler install failed: %s", exc)
    return _handler


class TrayIcon:
    """System-tray icon with a green ball that shows/hides the console window."""

    def __init__(self, *, on_exit_requested: Callable[[], None]) -> None:
        self._on_exit_requested = on_exit_requested
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None
        self._console_visible = False
        self._close_handler: object = None

    # ------------------------------------------------------------------
    # Menu callbacks (called from the pystray thread)
    # ------------------------------------------------------------------

    def _console_menu_label(self, item: pystray.MenuItem) -> str:
        return "Fechar Console" if self._console_visible else "Abrir Console"

    def _toggle_console(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._console_visible = not self._console_visible
        set_console_visible(self._console_visible)
        icon.update_menu()

    def _on_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        icon.stop()
        self._on_exit_requested()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Hide the console window and show the tray icon."""
        set_console_visible(False)
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
        self._close_handler = _install_close_to_tray_handler(self)
        LOGGER.info("Tray icon started", extra={"category": "startup"})

    def stop(self) -> None:
        """Stop the tray icon and restore the console window."""
        if self._close_handler is not None:
            try:
                ctypes.windll.kernel32.SetConsoleCtrlHandler(self._close_handler, False)  # type: ignore[attr-defined]
            except Exception as exc:
                LOGGER.debug("SetConsoleCtrlHandler uninstall failed: %s", exc)
            self._close_handler = None
        if self._icon is not None:
            set_console_visible(True)
            try:
                self._icon.stop()
            except Exception as exc:
                LOGGER.debug("Tray icon stop error: %s", exc, extra={"category": "startup"})
            self._icon = None
