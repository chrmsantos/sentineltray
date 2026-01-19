from __future__ import annotations

import logging
import os
from threading import Event, Thread
from typing import Optional

from PIL import Image, ImageDraw
import pystray
import tkinter as tk
import tkinter.font as tkfont
import webbrowser

from .app import Notifier
from .config import AppConfig
from .status import StatusStore, format_status
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)


def _build_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), color=(28, 40, 56))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 18, 56, 46), outline=(255, 255, 255), width=3)
    draw.ellipse((24, 24, 40, 40), outline=(255, 255, 255), width=2)
    draw.ellipse((28, 28, 36, 36), fill=(90, 180, 255))
    return image


def _start_notifier(
    config: AppConfig,
    status: StatusStore,
    stop_event: Event,
    pause_event: Event,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(target=notifier.run_loop, args=(stop_event, pause_event), daemon=True)
    thread.start()
    return thread


def run_tray(config: AppConfig) -> None:
    status = StatusStore()
    stop_event = Event()
    pause_event = Event()
    notifier_thread = _start_notifier(config, status, stop_event, pause_event)

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
        error_window.title("SentinelTray - Atenção")
        error_window.resizable(False, False)

        title = tk.Label(
            error_window,
            text="Atenção: ocorreu um problema",
            anchor="w",
            font=("Segoe UI", 14, "bold"),
            fg="#cc0000",
        )
        title.pack(fill="x", padx=12, pady=(12, 4))

        error_label = tk.Label(
            error_window,
            text=message,
            justify="left",
            anchor="nw",
            font=("Segoe UI", 12),
            bg="#fff0f0",
            fg="#cc0000",
        )
        error_label.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        error_window.update_idletasks()
        error_window.geometry(
            f"{error_window.winfo_reqwidth()}x{error_window.winfo_reqheight()}"
        )

    def request_exit() -> None:
        stop_event.set()
        root.after(0, root.quit)

    def toggle_pause() -> None:
        if pause_event.is_set():
            pause_event.clear()
        else:
            pause_event.set()

    def show_status() -> None:
        nonlocal status_window, status_label
        if status_window is not None and status_window.winfo_exists():
            status_window.deiconify()
            status_window.lift()
            return

        status_window = tk.Toplevel(root)
        status_window.title("SentinelTray - Painel")
        status_window.resizable(False, False)

        title = tk.Label(
            status_window,
            text=f"SentinelTray - Monitor de tela (beta {__version_label__})",
            anchor="w",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(fill="x", padx=12, pady=(12, 2))

        subtitle = tk.Label(
            status_window,
            text=(
                "Acompanha o texto da tela e avisa por e-mail quando encontra algo novo "
                f"\u2022 {__release_date__}"
            ),
            anchor="w",
            font=("Segoe UI", 12),
        )
        subtitle.pack(fill="x", padx=12, pady=(0, 6))

        status_label = tk.Label(
            status_window,
            text=format_status(status.snapshot()),
            justify="left",
            anchor="nw",
            font=("Segoe UI", 12),
            bg="#f2f2f2",
        )
        status_label.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        config_path = os.path.join(os.environ.get("USERPROFILE", ""), "sentineltray", "config.local.yaml")
        data_dir = os.path.join(os.environ.get("USERPROFILE", ""), "sentineltray")
        logs_dir = os.path.join(os.environ.get("USERPROFILE", ""), "sentineltray", "logs")

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

        def open_logs_dir() -> None:
            if logs_dir:
                try:
                    os.startfile(logs_dir)
                except OSError:
                    return

        def copy_status() -> None:
            text = format_status(status.snapshot())
            try:
                status_window.clipboard_clear()
                status_window.clipboard_append(text)
            except tk.TclError:
                return

        def refresh_now() -> None:
            snapshot = status.snapshot()
            if status_label is not None and status_label.winfo_exists():
                status_label.config(text=format_status(snapshot))

        menu_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        item_font = tkfont.Font(family="Segoe UI", size=11, weight="normal")
        menu = tk.Menu(status_window, font=menu_font)
        commands_menu = tk.Menu(menu, tearoff=0, font=item_font)
        commands_menu.add_command(label="Pausar ou continuar", command=toggle_pause)
        commands_menu.add_command(label="Atualizar informações", command=refresh_now)
        commands_menu.add_command(label="Copiar informações", command=copy_status)
        commands_menu.add_separator()
        commands_menu.add_command(label="Abrir configurações", command=open_config)
        commands_menu.add_command(label="Abrir pasta de dados", command=open_data_dir)
        commands_menu.add_command(label="Abrir registros", command=open_logs_dir)
        commands_menu.add_command(label="Abrir site do projeto", command=open_repo)
        commands_menu.add_separator()
        commands_menu.add_command(label="Encerrar o programa", command=request_exit)
        menu.add_cascade(label="Menu", menu=commands_menu)
        status_window.config(menu=menu)

        status_window.update_idletasks()
        status_window.geometry(
            f"{status_window.winfo_reqwidth()}x{status_window.winfo_reqheight()}"
        )

    def on_status(_: pystray.Icon, __: pystray.MenuItem) -> None:
        root.after(0, show_status)

    def on_exit(_: pystray.Icon, __: pystray.MenuItem) -> None:
        request_exit()

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
