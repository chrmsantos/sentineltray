from __future__ import annotations

import logging
from threading import Event, Thread
from typing import Optional

from PIL import Image, ImageDraw
import pystray
import tkinter as tk
import webbrowser

from .app import Notifier
from .config import AppConfig
from .status import StatusStore, format_status

LOGGER = logging.getLogger(__name__)


def _build_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), color=(28, 40, 56))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 18, 56, 46), outline=(255, 255, 255), width=3)
    draw.ellipse((24, 24, 40, 40), outline=(255, 255, 255), width=2)
    draw.ellipse((28, 28, 36, 36), fill=(90, 180, 255))
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
        root.after(int(config.status_refresh_seconds * 1000), refresh_status)

    def show_error(message: str) -> None:
        nonlocal error_window, error_label, last_error_shown
        last_error_shown = message
        if error_window is not None and error_window.winfo_exists():
            error_label.config(text=message)
            error_window.deiconify()
            error_window.lift()
            return

        error_window = tk.Toplevel(root)
        error_window.title("SentinelTray - Erro")
        error_window.geometry("540x180")
        error_window.resizable(False, False)

        title = tk.Label(
            error_window,
            text="Alerta de erro",
            anchor="w",
            font=("Segoe UI", 11, "bold"),
            fg="#cc0000",
        )
        title.pack(fill="x", padx=12, pady=(12, 4))

        error_label = tk.Label(
            error_window,
            text=message,
            justify="left",
            anchor="nw",
            font=("Consolas", 10),
            bg="#fff0f0",
            fg="#cc0000",
        )
        error_label.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def show_status() -> None:
        nonlocal status_window, status_label
        if status_window is not None and status_window.winfo_exists():
            status_window.deiconify()
            status_window.lift()
            return

        status_window = tk.Toplevel(root)
        status_window.title("SentinelTray - Status")
        status_window.geometry("540x220")
        status_window.resizable(False, False)

        title = tk.Label(
            status_window,
            text="SentinelTray - Monitoramento de janelas",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )
        title.pack(fill="x", padx=12, pady=(12, 2))

        subtitle = tk.Label(
            status_window,
            text="Leitura de texto visivel e envio de alertas por e-mail",
            anchor="w",
            font=("Segoe UI", 10),
        )
        subtitle.pack(fill="x", padx=12, pady=(0, 6))

        status_label = tk.Label(
            status_window,
            text=format_status(status.snapshot()),
            justify="left",
            anchor="nw",
            font=("Consolas", 10),
            bg="#f2f2f2",
        )
        status_label.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        links = tk.Frame(status_window)
        links.pack(fill="x", padx=12, pady=(0, 12))

        config_path = os.path.join(os.environ.get("USERPROFILE", ""), "sentineltray", "config.local.yaml")
        data_dir = os.path.join(os.environ.get("USERPROFILE", ""), "sentineltray")

        def open_config() -> None:
            if config_path:
                try:
                    os.startfile(config_path)
                except OSError:
                    return

        def open_repo() -> None:
            webbrowser.open("https://github.com/chrmsantos/sentineltray")

        def open_data_dir() -> None:
            if data_dir:
                try:
                    os.startfile(data_dir)
                except OSError:
                    return

        btn_config = tk.Button(links, text="Abrir configuracoes", command=open_config)
        btn_repo = tk.Button(links, text="Abrir repositorio", command=open_repo)
        btn_dir = tk.Button(links, text="Abrir pasta de dados", command=open_data_dir)
        btn_config.pack(side="left")
        btn_dir.pack(side="left", padx=(8, 0))
        btn_repo.pack(side="right")

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
            pystray.MenuItem("Abrir status", on_status, default=True),
            pystray.MenuItem("Sair", on_exit),
        ),
    )

    icon.run_detached()
    root.after(0, show_status)
    root.after(1000, refresh_status)
    root.mainloop()

    icon.stop()
    stop_event.set()
    notifier_thread.join(timeout=5)
