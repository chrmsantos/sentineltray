from __future__ import annotations

import logging
from threading import Event, Thread
from typing import Optional

from PIL import Image, ImageDraw
import pystray
import tkinter as tk

from .app import Notifier
from .config import AppConfig
from .status import StatusStore, format_status

LOGGER = logging.getLogger(__name__)


def _build_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 56), outline=(0, 200, 0), width=4)
    draw.rectangle((20, 20, 44, 44), fill=(0, 200, 0))
    return image


def _start_notifier(config: AppConfig, status: StatusStore, stop_event: Event) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(target=notifier.run_loop, args=(stop_event,), daemon=True)
    thread.start()
    return thread


def run_tray(config: AppConfig) -> None:
    status = StatusStore()
    stop_event = Event()
    notifier_thread = _start_notifier(config, status, stop_event)

    root = tk.Tk()
    root.withdraw()

    status_window: Optional[tk.Toplevel] = None
    status_label: Optional[tk.Label] = None
    error_window: Optional[tk.Toplevel] = None
    error_label: Optional[tk.Label] = None
    last_error_shown = ""

    def refresh_status() -> None:
        nonlocal status_label
        snapshot = status.snapshot()
        if status_label is not None and status_label.winfo_exists():
            status_label.config(text=format_status(snapshot))
        if (
            config.show_error_window
            and snapshot.last_error
            and snapshot.last_error != last_error_shown
        ):
            show_error(snapshot.last_error)
        root.after(1000, refresh_status)

    def show_error(message: str) -> None:
        nonlocal error_window, error_label, last_error_shown
        last_error_shown = message
        if error_window is not None and error_window.winfo_exists():
            error_label.config(text=message)
            error_window.deiconify()
            error_window.lift()
            return

        error_window = tk.Toplevel(root)
        error_window.title("SentinelTray Error")
        error_window.geometry("520x160")
        error_window.resizable(False, False)

        error_label = tk.Label(
            error_window,
            text=message,
            justify="left",
            anchor="nw",
            font=("Consolas", 10),
            fg="#cc0000",
        )
        error_label.pack(fill="both", expand=True, padx=10, pady=10)

    def show_status() -> None:
        nonlocal status_window, status_label
        if status_window is not None and status_window.winfo_exists():
            status_window.deiconify()
            status_window.lift()
            return

        status_window = tk.Toplevel(root)
        status_window.title("SentinelTray Status")
        status_window.geometry("520x180")
        status_window.resizable(False, False)

        status_label = tk.Label(
            status_window,
            text=format_status(status.snapshot()),
            justify="left",
            anchor="nw",
            font=("Consolas", 10),
        )
        status_label.pack(fill="both", expand=True, padx=10, pady=10)

    def on_status(_: pystray.Icon, __: pystray.MenuItem) -> None:
        root.after(0, show_status)

    def on_exit(_: pystray.Icon, __: pystray.MenuItem) -> None:
        stop_event.set()
        root.after(0, root.quit)

    icon = pystray.Icon(
        "sentineltray",
        _build_image(),
        "SentinelTray",
        menu=pystray.Menu(
            pystray.MenuItem("Status", on_status),
            pystray.MenuItem("Exit", on_exit),
        ),
    )

    icon.run_detached()
    root.after(1000, refresh_status)
    root.mainloop()

    icon.stop()
    stop_event.set()
    notifier_thread.join(timeout=5)
