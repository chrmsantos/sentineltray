from __future__ import annotations

import ctypes
import logging
import os
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
from typing import Optional

from PIL import Image, ImageDraw, ImageTk
import pystray
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
import webbrowser
import yaml

from .app import Notifier
from .config import AppConfig, get_project_root, get_user_data_dir
from .detector import WindowTextDetector, WindowUnavailableError
from .email_sender import build_sender
from .status import StatusStore, format_status
from . import __release_date__, __version_label__
from .whatsapp_sender import WhatsAppError, WhatsAppSender

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
    manual_scan_event: Event,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    thread = Thread(
        target=notifier.run_loop,
        args=(stop_event, pause_event, manual_scan_event),
        daemon=True,
    )
    thread.start()
    return thread


def _get_active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        handle = user32.GetForegroundWindow()
        if not handle:
            return ""
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, length + 1)
        return buffer.value.strip()
    except Exception:
        LOGGER.debug("Failed to resolve active window title", exc_info=True)
        return ""


def run_tray(config: AppConfig) -> None:
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

    def _notify_startup_error(message: str) -> None:
        messagebox.showerror(
            "Falha na inicialização",
            f"{message}\n\nAjuste as configurações e reabra o programa.",
        )
        try:
            sender = build_sender(config.email)
            sender.send(f"error: {message}")
        except Exception as exc:
            LOGGER.warning(
                "Startup email notification failed: %s",
                exc,
                extra={"category": "error"},
            )

    def _run_startup_validation() -> bool:
        messagebox.showinfo(
            "Preparação",
            "Antes de continuar, mantenha a janela a ser monitorada aberta "
            "(pode estar minimizada) e o WhatsApp Desktop aberto e logado.",
        )
        try:
            detector = WindowTextDetector(
                config.window_title_regex,
                allow_window_restore=config.allow_window_restore,
                log_throttle_seconds=config.log_throttle_seconds,
            )
            detector.check_ready()
        except WindowUnavailableError as exc:
            _notify_startup_error(f"Janela monitorada indisponível: {exc}")
            return False
        except Exception as exc:
            _notify_startup_error(f"Falha ao validar janela monitorada: {exc}")
            return False

        if config.whatsapp.enabled:
            try:
                whatsapp = WhatsAppSender(
                    config=config.whatsapp,
                    log_throttle_seconds=config.log_throttle_seconds,
                )
                whatsapp.check_ready()
            except WhatsAppError as exc:
                _notify_startup_error(f"WhatsApp indisponível: {exc}")
                return False
            except Exception as exc:
                _notify_startup_error(f"Falha ao validar WhatsApp: {exc}")
                return False
        return True

    if not _run_startup_validation():
        root.after(0, root.quit)
        root.mainloop()
        return

    status = StatusStore()
    stop_event = Event()
    pause_event = Event()
    manual_scan_event = Event()
    notifier_thread = _start_notifier(
        config, status, stop_event, pause_event, manual_scan_event
    )

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

    def request_restart() -> None:
        try:
            root_dir = get_project_root()
            run_cmd = root_dir / "scripts" / "run.cmd"
            if run_cmd.exists():
                subprocess.Popen(
                    ["cmd", "/c", str(run_cmd)],
                    cwd=str(root_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        finally:
            request_exit()

    def request_update() -> None:
        root_dir = get_project_root()
        install_cmd = root_dir / "install.cmd"
        if not install_cmd.exists():
            messagebox.showerror(
                "Atualização",
                "Script de atualização não encontrado.",
            )
            return
        subprocess.Popen(
            ["cmd", "/c", str(install_cmd), "/update"],
            cwd=str(root_dir),
        )
        messagebox.showinfo(
            "Atualização",
            "Atualização iniciada em segundo plano.",
        )

    def toggle_pause() -> None:
        if pause_event.is_set():
            pause_event.clear()
        else:
            pause_event.set()

    def request_manual_scan() -> None:
        LOGGER.info("Manual scan requested via UI", extra={"category": "control"})
        manual_scan_event.set()

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
        config_path = base_dir / "config.local.yaml"
        data_dir = str(base_dir)
        logs_dir = str(Path(config.log_file).parent)

        def save_config_update(
            *,
            window_title_regex: str | None = None,
            phrase_regex: str | None = None,
            whatsapp_contact_name: str | None = None,
            whatsapp_message_template: str | None = None,
        ) -> bool:
            nonlocal config
            if not config_path.exists():
                messagebox.showerror(
                    "Configuração",
                    "Arquivo config.local.yaml não encontrado."
                    "\nAbra as configurações e salve o arquivo primeiro.",
                )
                return False
            try:
                data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                messagebox.showerror(
                    "Configuração",
                    f"Falha ao ler config.local.yaml:\n{exc}",
                )
                return False

            if window_title_regex is not None:
                data["window_title_regex"] = window_title_regex
            if phrase_regex is not None:
                data["phrase_regex"] = phrase_regex

            if whatsapp_contact_name is not None or whatsapp_message_template is not None:
                whatsapp = data.get("whatsapp")
                if not isinstance(whatsapp, dict):
                    whatsapp = {}
                    data["whatsapp"] = whatsapp
                if whatsapp_contact_name is not None:
                    whatsapp["contact_name"] = whatsapp_contact_name
                if whatsapp_message_template is not None:
                    whatsapp["message_template"] = whatsapp_message_template
                whatsapp["enabled"] = True

            monitors = data.get("monitors")
            if isinstance(monitors, list) and monitors:
                first = monitors[0]
                if isinstance(first, dict):
                    if window_title_regex is not None:
                        first["window_title_regex"] = window_title_regex
                    if phrase_regex is not None:
                        first["phrase_regex"] = phrase_regex

            try:
                config_path.write_text(
                    yaml.safe_dump(
                        data,
                        sort_keys=False,
                        allow_unicode=True,
                    ),
                    encoding="utf-8",
                )
            except Exception as exc:
                messagebox.showerror(
                    "Configuração",
                    f"Falha ao salvar config.local.yaml:\n{exc}",
                )
                return False

            if window_title_regex is not None:
                config = replace(config, window_title_regex=window_title_regex)
            if phrase_regex is not None:
                config = replace(config, phrase_regex=phrase_regex)
            if whatsapp_contact_name is not None or whatsapp_message_template is not None:
                whatsapp = config.whatsapp
                if whatsapp_contact_name is not None:
                    whatsapp = replace(whatsapp, contact_name=whatsapp_contact_name)
                if whatsapp_message_template is not None:
                    whatsapp = replace(
                        whatsapp, message_template=whatsapp_message_template
                    )
                whatsapp = replace(whatsapp, enabled=True)
                config = replace(config, whatsapp=whatsapp)
            return True

        def open_config() -> None:
            try:
                os.startfile(str(config_path))
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

        def update_window_from_active() -> None:
            title = _get_active_window_title()
            if not title:
                messagebox.showwarning(
                    "Atualizar janela",
                    "Não foi possível identificar a janela ativa.",
                )
                return
            if save_config_update(window_title_regex=title):
                messagebox.showinfo(
                    "Atualizar janela",
                    "Janela monitorada atualizada no config.local.yaml."
                    "\nReinicie o aplicativo para aplicar na execução.",
                )
                refresh_now()

        def update_phrase_from_input() -> None:
            value = simpledialog.askstring(
                "Atualizar texto monitorado",
                "Informe o texto (regex) a ser monitorado:",
                initialvalue=config.phrase_regex,
                parent=status_window,
            )
            if value is None:
                return
            if save_config_update(phrase_regex=value):
                messagebox.showinfo(
                    "Atualizar texto",
                    "Texto monitorado atualizado no config.local.yaml."
                    "\nReinicie o aplicativo para aplicar na execução.",
                )
                refresh_now()

        def update_whatsapp_contact() -> None:
            value = simpledialog.askstring(
                "Atualizar destinatário WhatsApp",
                "Informe o nome do contato ou grupo:",
                initialvalue=config.whatsapp.contact_name,
                parent=status_window,
            )
            if value is None:
                return
            if save_config_update(whatsapp_contact_name=value):
                messagebox.showinfo(
                    "WhatsApp",
                    "Destinatário atualizado no config.local.yaml."
                    "\nReinicie o aplicativo para aplicar na execução.",
                )
                refresh_now()

        def update_whatsapp_message() -> None:
            value = simpledialog.askstring(
                "Atualizar mensagem WhatsApp",
                "Informe o texto da mensagem WhatsApp:",
                initialvalue=config.whatsapp.message_template,
                parent=status_window,
            )
            if value is None:
                return
            if save_config_update(whatsapp_message_template=value):
                messagebox.showinfo(
                    "WhatsApp",
                    "Mensagem atualizada no config.local.yaml."
                    "\nReinicie o aplicativo para aplicar na execução.",
                )
                refresh_now()

        menu_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        item_font = tkfont.Font(family="Segoe UI", size=11, weight="normal")
        menu = tk.Menu(status_window, font=menu_font)

        file_menu = tk.Menu(menu, tearoff=0, font=item_font)
        file_menu.add_command(label="Atualizar", command=request_update)
        file_menu.add_command(label="Reiniciar", command=request_restart)
        file_menu.add_command(label="Sair", command=request_exit)
        menu.add_cascade(label="Arquivo", menu=file_menu)

        view_menu = tk.Menu(menu, tearoff=0, font=item_font)
        view_menu.add_command(label="Atualizar agora", command=refresh_now)
        view_menu.add_command(label="Copiar status", command=copy_status)
        menu.add_cascade(label="Exibir", menu=view_menu)

        actions_menu = tk.Menu(menu, tearoff=0, font=item_font)
        actions_menu.add_command(label="Pausar ou continuar", command=toggle_pause)
        actions_menu.add_command(label="Executar teste imediato", command=request_manual_scan)
        actions_menu.add_separator()
        actions_menu.add_command(
            label="Atualizar janela monitorada", command=update_window_from_active
        )
        actions_menu.add_command(
            label="Atualizar texto monitorado", command=update_phrase_from_input
        )
        actions_menu.add_separator()
        actions_menu.add_command(
            label="Atualizar destinatário WhatsApp", command=update_whatsapp_contact
        )
        actions_menu.add_command(
            label="Atualizar mensagem WhatsApp", command=update_whatsapp_message
        )
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
            pystray.MenuItem("Executar teste imediato", lambda *_: request_manual_scan()),
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
