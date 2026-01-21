from __future__ import annotations

import ctypes
import logging
import time
from threading import Event, Thread

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

    exit_code: dict[str, int] = {"code": 0}
    icon_started_at = time.monotonic()

    def on_open(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        _show_console()

    def on_exit(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        exit_event.set()
        _icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Abrir", on_open, default=True),
        pystray.MenuItem("Sair", on_exit),
    )

    def run_cli_worker() -> None:
        try:
            exit_code["code"] = run_cli(config, exit_event=exit_event)
        finally:
            exit_event.set()
            try:
                icon.stop()
            except Exception:
                LOGGER.debug("Failed to stop tray icon", exc_info=True)

    def setup_icon(_icon: pystray.Icon) -> None:
        LOGGER.info("Tray icon starting", extra={"category": "startup"})
        _icon.visible = True
        elapsed_ms = (time.monotonic() - icon_started_at) * 1000
        LOGGER.info(
            "Tray icon visible after %.0f ms",
            elapsed_ms,
            extra={"category": "startup"},
        )

    worker = Thread(target=run_cli_worker, daemon=True)
    _install_console_close_handler()
    _hide_console()
    worker.start()

    try:
        icon.run(setup=setup_icon)
    except Exception:
        LOGGER.exception("Tray icon failed to start", extra={"category": "startup"})
    finally:
        exit_event.set()
        worker.join(timeout=5)

    return exit_code["code"]