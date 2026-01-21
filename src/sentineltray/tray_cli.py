from __future__ import annotations

import ctypes
import logging
from threading import Event

from PIL import Image, ImageDraw
import pystray

from .cli import run_cli
from .config import AppConfig

LOGGER = logging.getLogger(__name__)

_SW_HIDE = 0
_SW_SHOW = 5


def _console_handle() -> int:
    return int(ctypes.windll.kernel32.GetConsoleWindow())


def _hide_console() -> None:
    handle = _console_handle()
    if handle:
        ctypes.windll.user32.ShowWindow(handle, _SW_HIDE)


def _show_console() -> None:
    handle = _console_handle()
    if handle:
        ctypes.windll.user32.ShowWindow(handle, _SW_SHOW)
        ctypes.windll.user32.SetForegroundWindow(handle)


def _install_console_close_handler() -> object:
    handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

    def handler(ctrl_type: int) -> bool:
        if ctrl_type in {2, 5, 6}:
            _hide_console()
            return True
        return False

    callback = handler_type(handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(callback, True)
    return callback


def _build_icon_image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = 18
    center = (32, 32)
    draw.ellipse(
        (
            center[0] - radius,
            center[1] - radius,
            center[0] + radius,
            center[1] + radius,
        ),
        fill=(0, 200, 0, 255),
        outline=(0, 120, 0, 255),
        width=2,
    )
    return image


def run_tray_cli(config: AppConfig) -> int:
    exit_event = Event()
    icon = pystray.Icon(
        "sentineltray",
        _build_icon_image(),
        "SentinelTray: Monitorando",
    )

    def on_open(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        _show_console()

    def on_exit(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        exit_event.set()
        _icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Abrir", on_open, default=True),
        pystray.MenuItem("Sair", on_exit),
    )

    icon.run_detached()
    _install_console_close_handler()
    _hide_console()

    try:
        return run_cli(config, exit_event=exit_event)
    finally:
        try:
            icon.stop()
        except Exception:
            LOGGER.debug("Failed to stop tray icon", exc_info=True)