from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Event, Thread
from typing import Optional

from PIL import Image, ImageDraw, ImageTk
import pystray
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox
import webbrowser

from .app import Notifier
from .config import AppConfig, get_user_data_dir
from .status import StatusStore, format_status
from . import __release_date__, __version_label__

LOGGER = logging.getLogger(__name__)

STATUS_REFRESH_SECONDS = 10
LICENSE_LABEL = "GPL-3.0-only"


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

    icon_image = _build_image()
    icon_photo = ImageTk.PhotoImage(icon_image)
    root.iconphoto(True, icon_photo)

    status_window: Optional[tk.Toplevel] = None
    status_label: Optional[tk.Label] = None
    error_window: Optional[tk.Toplevel] = None
    error_label: Optional[tk.Label] = None
    last_error_shown = ""

    def refresh_status() -> None:
        nonlocal status_label
        snapshot = status.snapshot()
        if status_label is not None and status_label.winfo_exists():
            status_label.config(
                    text=format_status(
                        snapshot,
                        window_title_regex=config.window_title_regex,
                        phrase_regex=config.phrase_regex,
                        poll_interval_seconds=config.poll_interval_seconds,
                    )
            )
        # Erros ficam apenas registrados no painel principal.
        root.after(int(STATUS_REFRESH_SECONDS * 1000), refresh_status)

    def show_error(_message: str) -> None:
        # Mantido apenas para compatibilidade interna; janela removida.
        nonlocal last_error_shown
        last_error_shown = _message

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
        status_window.iconphoto(True, icon_photo)

        title = tk.Label(
            status_window,
            text="SentinelTray - Monitor de tela",
            anchor="w",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(fill="x", padx=12, pady=(12, 2))

        subtitle = tk.Label(
            status_window,
            text=(
                "Acompanha o texto da tela e avisa por e-mail quando encontra algo novo"
            ),
            anchor="w",
            font=("Segoe UI", 12),
        )
        subtitle.pack(fill="x", padx=12, pady=(0, 6))

        version_label = tk.Label(
            status_window,
            text=f"Beta {__version_label__} \u2022 {__release_date__}",
            anchor="w",
            font=("Segoe UI", 9),
            fg="#666666",
        )
        version_label.pack(fill="x", padx=12, pady=(0, 6))

        license_label = tk.Label(
            status_window,
            text=f"Licença: {LICENSE_LABEL}",
            anchor="w",
            font=("Segoe UI", 9),
            fg="#666666",
        )
        license_label.pack(fill="x", padx=12, pady=(0, 8))

        status_label = tk.Label(
            status_window,
                text=format_status(
                    status.snapshot(),
                    window_title_regex=config.window_title_regex,
                    phrase_regex=config.phrase_regex,
                    poll_interval_seconds=config.poll_interval_seconds,
                ),
            justify="left",
            anchor="nw",
            font=("Segoe UI", 12),
            bg="#f2f2f2",
        )
        status_label.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        base_dir = get_user_data_dir()
        config_path = str(base_dir / "config.local.yaml")
        data_dir = str(base_dir)
        logs_dir = str(Path(config.log_file).parent)

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
            text = format_status(
                status.snapshot(),
                window_title_regex=config.window_title_regex,
                phrase_regex=config.phrase_regex,
            )
            try:
                status_window.clipboard_clear()
                status_window.clipboard_append(text)
            except tk.TclError:
                return

        def refresh_now() -> None:
            snapshot = status.snapshot()
            if status_label is not None and status_label.winfo_exists():
                status_label.config(
                        text=format_status(
                            snapshot,
                            window_title_regex=config.window_title_regex,
                            phrase_regex=config.phrase_regex,
                            poll_interval_seconds=config.poll_interval_seconds,
                        )
                )

        menu_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        item_font = tkfont.Font(family="Segoe UI", size=11, weight="normal")
        menu = tk.Menu(status_window, font=menu_font)

        file_menu = tk.Menu(menu, tearoff=0, font=item_font)
        file_menu.add_command(label="Sair", command=request_exit)
        menu.add_cascade(label="Arquivo", menu=file_menu)

        view_menu = tk.Menu(menu, tearoff=0, font=item_font)
        view_menu.add_command(label="Atualizar agora", command=refresh_now)
        view_menu.add_command(label="Copiar status", command=copy_status)
        menu.add_cascade(label="Exibir", menu=view_menu)

        actions_menu = tk.Menu(menu, tearoff=0, font=item_font)
        actions_menu.add_command(label="Pausar ou continuar", command=toggle_pause)
        actions_menu.add_separator()
        actions_menu.add_command(label="Abrir configurações", command=open_config)
        actions_menu.add_command(label="Abrir pasta de dados", command=open_data_dir)
        actions_menu.add_command(label="Abrir registros", command=open_logs_dir)
        menu.add_cascade(label="Ações", menu=actions_menu)

        help_menu = tk.Menu(menu, tearoff=0, font=item_font)
        help_menu.add_command(label="Site do projeto", command=open_repo)
        help_menu.add_command(
            label="Sobre",
            command=lambda: messagebox.showinfo(
                "Sobre",
                f"SentinelTray\nVersão {__version_label__}\nLicença {LICENSE_LABEL}",
            ),
        )
        menu.add_cascade(label="Ajuda", menu=help_menu)

        status_window.config(menu=menu)

        status_window.update_idletasks()
        req_width = status_window.winfo_reqwidth()
        req_height = status_window.winfo_reqheight()
        width = max(req_width, 640)
        status_window.minsize(width, req_height)
        status_window.geometry(f"{width}x{req_height}")

    def on_status(_: pystray.Icon, __: pystray.MenuItem) -> None:
        root.after(0, show_status)

    def on_exit(_: pystray.Icon, __: pystray.MenuItem) -> None:
        request_exit()

    icon = pystray.Icon(
        "sentineltray",
        icon_image,
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
