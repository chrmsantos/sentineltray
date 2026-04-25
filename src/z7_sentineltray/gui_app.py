from __future__ import annotations

import json
import logging
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Callable

import tkinter as tk
from tkinter import messagebox

from .app import Notifier
from .config import AppConfig, get_project_root, get_user_data_dir, load_config
from .status import StatusStore, format_timestamp
from .tray_app import TrayIcon, set_console_visible

LOGGER = logging.getLogger(__name__)
_PROJECT_REPO_URL = "https://github.com/chrmsantos/z7_sentineltray"

# ── GitHub-dark-inspired palette ─────────────────────────────────────────────
_BG      = "#0d1117"   # main background
_SURFACE = "#161b22"   # header / footer surface
_CARD    = "#1c2128"   # card background
_BORDER  = "#30363d"   # borders
_GREEN   = "#3fb950"   # primary accent (running)
_GREEN2  = "#196127"   # dark green
_RED     = "#f85149"   # error / stopped
_AMBER   = "#d29922"   # warning
_BLUE    = "#58a6ff"   # scan button
_TEXT    = "#c9d1d9"   # primary text
_MUTED   = "#8b949e"   # secondary text
_WHITE   = "#e6edf3"   # bright text
_BTN_DIM = "#21262d"   # dim button bg


# ── Theme palettes ────────────────────────────────────────────────────────────
_DARK_PALETTE: dict[str, str] = {
    "bg": _BG, "surface": _SURFACE, "card": _CARD, "border": _BORDER,
    "green": _GREEN, "green2": _GREEN2, "red": _RED, "amber": _AMBER,
    "blue": _BLUE, "text": _TEXT, "muted": _MUTED, "white": _WHITE,
    "btn_dim": _BTN_DIM, "exit_btn": "#5a1a1a", "select_bg": "#264f78",
}

_LIGHT_PALETTE: dict[str, str] = {
    "bg": "#ffffff", "surface": "#f6f8fa", "card": "#ffffff", "border": "#d0d7de",
    "green": "#1a7f37", "green2": "#2da44e", "red": "#cf222e", "amber": "#9a6700",
    "blue": "#0969da", "text": "#1f2328", "muted": "#656d76", "white": "#1f2328",
    "btn_dim": "#e6eaef", "exit_btn": "#ffd8d8", "select_bg": "#b6d3fb",
}


def _apply_theme_walk(root: tk.Widget, old_pal: dict, new_pal: dict) -> None:
    """Recursively remap palette colors across all widgets."""
    color_map = {v: new_pal[k] for k, v in old_pal.items()}
    _OPTS = ("bg", "fg", "activebackground", "activeforeground",
             "insertbackground", "selectbackground")

    def _remap(w: tk.Widget) -> None:
        for opt in _OPTS:
            try:
                cur = w.cget(opt)
                if cur in color_map:
                    w.configure(**{opt: color_map[cur]})
            except tk.TclError:
                pass
        for child in w.winfo_children():
            _remap(child)

    _remap(root)


class _ThemeState:
    """Persisted holder for the active UI theme."""

    def __init__(self) -> None:
        self._dark = True
        self._load()

    def _pref_path(self) -> Path:
        return get_user_data_dir() / "ui_prefs.json"

    def _load(self) -> None:
        try:
            data = json.loads(self._pref_path().read_text(encoding="utf-8"))
            self._dark = bool(data.get("dark_theme", True))
        except Exception:
            self._dark = True

    def _save(self) -> None:
        try:
            p = self._pref_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"dark_theme": self._dark}), encoding="utf-8")
        except Exception:
            pass

    @property
    def is_dark(self) -> bool:
        return self._dark

    @property
    def palette(self) -> dict:
        return _DARK_PALETTE if self._dark else _LIGHT_PALETTE

    def toggle(self, root: tk.Widget) -> None:
        old = self.palette
        self._dark = not self._dark
        self._save()
        _apply_theme_walk(root, old, self.palette)


# ─────────────────────────────────────────────────────────────────────────────
# SMTP password dialog
# ─────────────────────────────────────────────────────────────────────────────

def prompt_smtp_password_gui(username: str, monitor_index: int) -> str | None:
    """Show a modal dialog to collect the SMTP password.

    Returns the entered password, or ``None`` if the user cancelled.
    """
    result: list[str | None] = [None]

    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("Z7_SentinelTray — Senha SMTP")
    dialog.configure(bg=_BG)
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus_force()

    dialog.update_idletasks()
    width, height = 380, 200
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(
        dialog,
        text=f"Usuário SMTP (monitor {monitor_index}):",
        bg=_BG,
        fg=_MUTED,
        font=("Segoe UI", 9),
    ).pack(pady=(18, 2))
    tk.Label(
        dialog,
        text=username,
        bg=_BG,
        fg=_WHITE,
        font=("Segoe UI", 10, "bold"),
    ).pack()
    tk.Label(
        dialog,
        text="Senha SMTP:",
        bg=_BG,
        fg=_MUTED,
        font=("Segoe UI", 9),
    ).pack(pady=(12, 2))
    entry = tk.Entry(
        dialog,
        show="*",
        bg=_SURFACE,
        fg=_TEXT,
        insertbackground=_TEXT,
        relief="flat",
        font=("Segoe UI", 10),
        width=32,
    )
    entry.pack(padx=24)
    entry.focus_set()

    def on_ok() -> None:
        result[0] = entry.get()
        dialog.destroy()

    def on_cancel() -> None:
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=_BG)
    btn_frame.pack(pady=14)
    tk.Button(
        btn_frame,
        text="OK",
        command=on_ok,
        bg=_GREEN2,
        fg=_WHITE,
        relief="flat",
        padx=20,
        font=("Segoe UI", 9),
    ).pack(side="left", padx=6)
    tk.Button(
        btn_frame,
        text="Cancelar",
        command=on_cancel,
        bg=_BTN_DIM,
        fg=_TEXT,
        relief="flat",
        padx=10,
        font=("Segoe UI", 9),
    ).pack(side="left", padx=6)

    entry.bind("<Return>", lambda _e: on_ok())
    dialog.bind("<Escape>", lambda _e: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    root.wait_window(dialog)
    root.destroy()
    return result[0]


# ─────────────────────────────────────────────────────────────────────────────
# In-app YAML config editor
# ─────────────────────────────────────────────────────────────────────────────

class ConfigEditorWindow:
    """Modal-like Toplevel that lets the user edit config.local.yaml in-app."""

    def __init__(
        self,
        parent: tk.Tk,
        *,
        on_saved: Callable[[AppConfig], None],
        theme_state: "_ThemeState | None" = None,
    ) -> None:
        self._parent = parent
        self._on_saved = on_saved
        self._theme = theme_state
        self._win: tk.Toplevel | None = None
        self._text: tk.Text | None = None
        self._lineno: tk.Text | None = None
        self._status_var = tk.StringVar()
        self._status_color = tk.StringVar(value=_MUTED)
        self._status_lbl: tk.Label | None = None
        self._cfg_path = get_user_data_dir() / "config.local.yaml"

    # ── Public ────────────────────────────────────────────────────────────────

    def show(self) -> None:
        if self._win is not None and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
            return
        self._build()
        self._load_file()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        win = tk.Toplevel(self._parent)
        self._win = win
        win.title("Z7_SentinelTray — Editor de Configuração")
        win.configure(bg=_BG)
        win.geometry("860x620")
        win.minsize(600, 400)
        win.resizable(True, True)
        win.transient(self._parent)
        win.grab_set()

        try:
            if self._parent.iconbitmap():
                win.iconbitmap(self._parent.iconbitmap())
        except Exception:
            pass

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = tk.Frame(win, bg=_SURFACE, pady=8)
        toolbar.pack(fill=tk.X)
        tk.Label(toolbar, text="⚙  config.local.yaml",
                 font=("Segoe UI", 10, "bold"), fg=_GREEN, bg=_SURFACE).pack(
            side=tk.LEFT, padx=14)
        tk.Label(toolbar, text=str(self._cfg_path),
                 font=("Segoe UI", 8), fg=_MUTED, bg=_SURFACE).pack(
            side=tk.LEFT, padx=(0, 14))
        tk.Frame(win, bg=_BORDER, height=1).pack(fill=tk.X)

        # ── Editor area ───────────────────────────────────────────────────────
        editor_frame = tk.Frame(win, bg=_BG)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        # Line-number gutter
        ln = tk.Text(
            editor_frame,
            width=4, padx=6, takefocus=0, state="disabled",
            font=("Consolas", 11), bg="#0d1117", fg=_MUTED,
            relief=tk.FLAT, bd=0, wrap=tk.NONE,
            cursor="arrow",
        )
        ln.pack(side=tk.LEFT, fill=tk.Y)
        self._lineno = ln

        tk.Frame(editor_frame, bg=_BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Main text widget + scrollbars
        text_container = tk.Frame(editor_frame, bg=_BG)
        text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = tk.Scrollbar(text_container, orient=tk.VERTICAL)
        hsb = tk.Scrollbar(text_container, orient=tk.HORIZONTAL)
        txt = tk.Text(
            text_container,
            font=("Consolas", 11),
            bg="#0d1117", fg=_TEXT,
            insertbackground=_GREEN,
            selectbackground="#264f78",
            relief=tk.FLAT, bd=0,
            wrap=tk.NONE,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            undo=True,
            tabs=("2.0c",),
        )
        vsb.config(command=self._sync_scroll)
        hsb.config(command=txt.xview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        txt.pack(fill=tk.BOTH, expand=True)
        self._text = txt
        self._vsb = vsb

        # Sync line numbers on key/scroll
        txt.bind("<KeyRelease>", lambda e: self._update_linenos())
        txt.bind("<MouseWheel>", lambda e: self._after_scroll())
        txt.bind("<Button-4>", lambda e: self._after_scroll())
        txt.bind("<Button-5>", lambda e: self._after_scroll())
        txt.bind("<<Modified>>", lambda e: self._on_modified())

        # ── Status bar ────────────────────────────────────────────────────────
        tk.Frame(win, bg=_BORDER, height=1).pack(fill=tk.X)
        status_bar = tk.Frame(win, bg=_SURFACE, pady=4)
        status_bar.pack(fill=tk.X)
        sl = tk.Label(status_bar, textvariable=self._status_var,
                      font=("Segoe UI", 8), fg=_MUTED, bg=_SURFACE, anchor="w")
        sl.pack(side=tk.LEFT, padx=14, fill=tk.X, expand=True)
        self._status_lbl = sl
        self._status_var.set("Pronto — Ctrl+S para salvar")

        # ── Footer buttons ────────────────────────────────────────────────────
        tk.Frame(win, bg=_BORDER, height=1).pack(fill=tk.X)
        footer = tk.Frame(win, bg=_SURFACE, pady=10)
        footer.pack(fill=tk.X)
        self._make_btn(footer, "✓  Validar", self._validate, _BTN_DIM).pack(
            side=tk.LEFT, padx=(14, 6))
        self._make_btn(footer, "💾  Salvar e Aplicar", self._save_apply, _GREEN2).pack(
            side=tk.LEFT, padx=(0, 6))
        self._make_btn(footer, "↺  Restaurar valores padrão", self._restore_defaults, _BTN_DIM).pack(
            side=tk.LEFT, padx=(0, 6))
        self._make_btn(footer, "Cancelar", win.destroy, "#5a1a1a").pack(
            side=tk.RIGHT, padx=(0, 14))

        # Keyboard shortcut
        win.bind("<Control-s>", lambda e: self._save_apply())
        win.bind("<Escape>", lambda e: win.destroy())

        # Apply light theme if active
        if self._theme is not None and not self._theme.is_dark:
            _apply_theme_walk(win, _DARK_PALETTE, _LIGHT_PALETTE)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_btn(self, parent: tk.Frame, text: str,
                  cmd: Callable[[], None], bg: str) -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Segoe UI", 9, "bold"),
            fg=_WHITE, bg=bg, activeforeground=_WHITE, activebackground=bg,
            relief=tk.FLAT, cursor="hand2", padx=12, pady=5, bd=0,
        )

    def _restore_defaults(self) -> None:
        import sys
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Restaurar valores padrão",
            "Isso substituirá o conteúdo do editor pelo template padrão.\n"
            "As alterações não salvas serão perdidas. Deseja continuar?",
            parent=self._win,
        ):
            return
        meipass = getattr(sys, "_MEIPASS", None)
        candidates = []
        if meipass:
            candidates.append(Path(meipass) / "config" / "config.local.yaml.example")
        candidates.append(get_project_root() / "config" / "config.local.yaml.example")
        template_content: str | None = None
        for example_path in candidates:
            try:
                template_content = example_path.read_text(encoding="utf-8")
                break
            except Exception:
                continue
        if template_content is None:
            self._set_status("✗ Template padrão não encontrado", _RED)
            return
        if self._text:
            self._text.delete("1.0", tk.END)
            self._text.insert("1.0", template_content)
            self._text.edit_reset()
            self._text.edit_modified(False)
        self._update_linenos()
        self._set_status("Valores padrão restaurados — Ctrl+S para salvar", _AMBER)

    def _load_file(self) -> None:
        self._cfg_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._cfg_path.exists():
            import sys
            meipass = getattr(sys, "_MEIPASS", None)
            candidates = []
            if meipass:
                candidates.append(Path(meipass) / "config" / "config.local.yaml.example")
            candidates.append(get_project_root() / "config" / "config.local.yaml.example")
            template_content: str | None = None
            for example_path in candidates:
                try:
                    template_content = example_path.read_text(encoding="utf-8")
                    break
                except Exception:
                    continue
            if template_content is None:
                template_content = "# Z7_SentinelTray — configuração local\n"
            self._cfg_path.write_text(template_content, encoding="utf-8")
        try:
            content = self._cfg_path.read_text(encoding="utf-8")
        except Exception as exc:
            content = f"# ERRO ao ler arquivo: {exc}\n"
        if self._text:
            self._text.delete("1.0", tk.END)
            self._text.insert("1.0", content)
            self._text.edit_reset()          # clear undo stack
            self._text.edit_modified(False)  # clear modified flag
        self._update_linenos()
        self._set_status("Arquivo carregado — Ctrl+S para salvar", _MUTED)

    def _update_linenos(self) -> None:
        txt = self._text
        ln = self._lineno
        if txt is None or ln is None:
            return
        # Determine visible line range
        first = int(txt.index("@0,0").split(".")[0])
        last_idx = txt.index(f"@0,{txt.winfo_height()}")
        last = int(last_idx.split(".")[0])
        total = int(txt.index(tk.END).split(".")[0]) - 1
        last = min(last + 1, total)
        ln.config(state="normal")
        ln.delete("1.0", tk.END)
        for i in range(first, last + 1):
            ln.insert(tk.END, f"{i}\n")
        ln.config(state="disabled")
        # Sync vertical position
        ln.yview_moveto(txt.yview()[0])

    def _sync_scroll(self, *args: object) -> None:
        if self._text:
            self._text.yview(*args)
        self._update_linenos()

    def _after_scroll(self) -> None:
        if self._win:
            self._win.after(20, self._update_linenos)

    def _on_modified(self) -> None:
        if self._text and self._text.edit_modified():
            self._set_status("Alterações não salvas — Ctrl+S para salvar", _AMBER)

    def _set_status(self, msg: str, color: str = _MUTED) -> None:
        self._status_var.set(msg)
        if self._status_lbl:
            self._status_lbl.configure(fg=color)

    def _get_content(self) -> str:
        if self._text is None:
            return ""
        return self._text.get("1.0", tk.END)

    def _validate(self) -> AppConfig | None:
        """Write to a temp path and parse; return AppConfig on success or None."""
        content = self._get_content()
        tmp = self._cfg_path.with_suffix(".yaml.validate_tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            cfg = load_config(str(tmp))
            self._set_status("✓ Configuração válida", _GREEN)
            return cfg
        except Exception as exc:
            self._set_status(f"✗ {exc}", _RED)
            return None
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _save_apply(self) -> None:
        cfg = self._validate()
        if cfg is None:
            return
        content = self._get_content()
        try:
            self._cfg_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            self._set_status(f"✗ Falha ao salvar: {exc}", _RED)
            return
        if self._text:
            self._text.edit_modified(False)
        self._set_status("✓ Salvo e aplicado", _GREEN)
        self._on_saved(cfg)
        if self._win:
            self._win.after(800, self._win.destroy)


class StatusWindow:
    """Beautiful tkinter status window for Z7_SentinelTray."""

    _REFRESH_MS = 1000

    def __init__(
        self,
        root: tk.Tk,
        status: StatusStore,
        config: AppConfig,
        *,
        get_config: Callable[[], AppConfig],
        on_manual_scan: Callable[[], None],
        on_open_config: Callable[[], None],
        on_exit: Callable[[], None],
        theme_state: "_ThemeState | None" = None,
    ) -> None:
        self._root = root
        self._status = status
        self._get_config = get_config
        self._on_manual_scan = on_manual_scan
        self._on_open_config = on_open_config
        self._on_exit = on_exit
        self._theme = theme_state or _ThemeState()
        self._visible = False
        self._after_id: str | None = None
        self._vars: dict[str, tk.StringVar] = {}
        self._value_labels: dict[str, tk.Label] = {}
        self._monitors_content: tk.Frame | None = None
        self._status_dot: tk.Label | None = None
        self._status_text: tk.Label | None = None
        self._theme_btn: tk.Button | None = None
        self._uptime_var = tk.StringVar(value="00:00:00")
        self._build_ui()
        if not self._theme.is_dark:
            _apply_theme_walk(self._root, _DARK_PALETTE, _LIGHT_PALETTE)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        r = self._root
        from . import __version_label__, __release_date__
        r.title(f"Z7_SentinelTray {__version_label__} ({__release_date__}) — Status")
        r.configure(bg=_BG)
        r.resizable(True, True)
        r.minsize(900, 480)
        r.protocol("WM_DELETE_WINDOW", self.hide)
        r.withdraw()

        # App icon
        try:
            from .path_utils import get_project_root as _gpr  # type: ignore[attr-defined]
            ico = _gpr() / "assets" / "icon.ico"
            if ico.exists():
                r.iconbitmap(str(ico))
        except Exception:
            pass

        W, H = 1080, 580
        self._center(W, H)
        r.geometry(f"{W}x{H}")

        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(r, bg=_SURFACE, pady=14)
        header.pack(fill=tk.X)

        eye = tk.Canvas(header, width=42, height=42, bg=_SURFACE, highlightthickness=0)
        eye.pack(side=tk.LEFT, padx=(18, 10))
        self._draw_eye(eye, 42)

        title_frame = tk.Frame(header, bg=_SURFACE)
        title_frame.pack(side=tk.LEFT)
        tk.Label(
            title_frame, text="Z7_SentinelTray",
            font=("Segoe UI", 15, "bold"), fg=_GREEN, bg=_SURFACE, anchor="w"
        ).pack(anchor="w")
        tk.Label(
            title_frame, text="Monitor de Janelas e Alertas",
            font=("Segoe UI", 9), fg=_MUTED, bg=_SURFACE, anchor="w"
        ).pack(anchor="w")

        tk.Label(
            header, text=f"v{__version_label__}  ·  {__release_date__}",
            font=("Segoe UI", 8), fg=_MUTED, bg=_SURFACE
        ).pack(side=tk.RIGHT, padx=18)

        tk.Frame(r, bg=_BORDER, height=1).pack(fill=tk.X)

        # ── Two-column body ───────────────────────────────────────────────────
        body_outer = tk.Frame(r, bg=_BG)
        body_outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        body_outer.columnconfigure(0, weight=1)
        body_outer.columnconfigure(1, weight=1)
        body_outer.rowconfigure(0, weight=1)

        left = tk.Frame(body_outer, bg=_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = tk.Frame(body_outer, bg=_BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ── LEFT: Status + Uptime row ─────────────────────────────────────────
        row1 = tk.Frame(left, bg=_BG)
        row1.pack(fill=tk.X, pady=(0, 10))

        sc, sc_c = self._make_card(row1, "STATUS")
        sc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        pill = tk.Frame(sc_c, bg=_CARD)
        pill.pack(pady=6)
        self._status_dot = tk.Label(pill, text="●", font=("Segoe UI", 22), fg=_AMBER, bg=_CARD)
        self._status_dot.pack(side=tk.LEFT)
        self._status_text = tk.Label(
            pill, text="INICIANDO", font=("Segoe UI", 14, "bold"), fg=_AMBER, bg=_CARD
        )
        self._status_text.pack(side=tk.LEFT, padx=(8, 0))

        uc, uc_c = self._make_card(row1, "TEMPO ATIVO")
        uc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(
            uc_c, textvariable=self._uptime_var,
            font=("Consolas", 20, "bold"), fg=_TEXT, bg=_CARD
        ).pack(pady=6)

        # ── LEFT: Scan Status ─────────────────────────────────────────────────
        self._kv_section(left, "VERIFICAÇÃO", [
            ("last_scan",   "Última Verificação"),
            ("next_scan",   "Próxima Verificação"),
            ("last_result", "Último Resultado"),
        ])

        # ── LEFT: Alerts ──────────────────────────────────────────────────────
        self._kv_section(left, "ALERTAS", [
            ("last_match",    "Última Detecção"),
            ("last_match_at", "Horário da Detecção"),
            ("last_send",     "Último Alerta Enviado"),
        ])

        # ── RIGHT: Errors ─────────────────────────────────────────────────────
        self._kv_section(right, "ERROS", [
            ("error_count",    "Total de Erros"),
            ("last_error",     "Último Erro"),
            ("breaker_active", "Disjuntores"),
        ])

        # ── RIGHT: Email Queue ────────────────────────────────────────────────
        eq_outer, eq_c = self._make_card(right, "FILA DE E-MAIL")
        eq_outer.pack(fill=tk.X, pady=(10, 0))
        for key, label, color in (
            ("q_pending",  "Pendente",  _AMBER),
            ("q_sent",     "Enviado",   _GREEN),
            ("q_failed",   "Falhou",    _RED),
            ("q_deferred", "Adiado",    _MUTED),
        ):
            cell = tk.Frame(eq_c, bg=_CARD)
            cell.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
            var = tk.StringVar(value="0")
            self._vars[key] = var
            tk.Label(cell, textvariable=var,
                     font=("Consolas", 22, "bold"), fg=color, bg=_CARD).pack()
            tk.Label(cell, text=label, font=("Segoe UI", 8), fg=_MUTED, bg=_CARD).pack()

        # ── RIGHT: Monitors ───────────────────────────────────────────────────
        mon_outer, mon_c = self._make_card(right, "MONITORES")
        mon_outer.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._monitors_content = mon_c

        # ── Footer ────────────────────────────────────────────────────────────
        tk.Frame(r, bg=_BORDER, height=1).pack(fill=tk.X)
        footer = tk.Frame(r, bg=_SURFACE, pady=10)
        footer.pack(fill=tk.X)

        self._make_btn(footer, "⟳  Verificar Agora", self._trigger_scan, _BLUE).pack(
            side=tk.LEFT, padx=(18, 6))
        self._make_btn(footer, "⚙  Configuração", self._on_open_config, _BTN_DIM).pack(
            side=tk.LEFT, padx=(0, 6))
        self._make_btn(footer, "↗  Repositório",
                       lambda: webbrowser.open(_PROJECT_REPO_URL), _BTN_DIM).pack(
            side=tk.LEFT)
        theme_label = "☀  Tema Claro" if self._theme.is_dark else "🌙  Tema Escuro"
        self._theme_btn = self._make_btn(footer, theme_label, self._toggle_theme, _BTN_DIM)
        self._theme_btn.pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(footer, text="Licenced under GPLv3 •  Câmara Municipal de Santa Bárbara d'Oeste/SP  •",
                 font=("Segoe UI", 8), fg=_MUTED, bg=_SURFACE).pack(
            side=tk.LEFT, padx=(12, 0))
        self._make_btn(footer, "Sair  ✕", self._on_exit, "#5a1a1a").pack(
            side=tk.RIGHT, padx=(0, 18))

    def _make_card(self, parent: tk.Widget, title: str) -> tuple[tk.Frame, tk.Frame]:
        """Create a styled card. Returns (outer, content). Caller packs outer."""
        outer = tk.Frame(parent, bg=_BORDER, padx=1, pady=1)
        inner = tk.Frame(outer, bg=_CARD)
        inner.pack(fill=tk.BOTH, expand=True)
        tk.Label(inner, text=title, font=("Segoe UI", 7, "bold"),
                 fg=_GREEN, bg=_CARD, anchor="w").pack(fill=tk.X, padx=12, pady=(8, 2))
        tk.Frame(inner, bg=_BORDER, height=1).pack(fill=tk.X, padx=12)
        content = tk.Frame(inner, bg=_CARD)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 10))
        return outer, content

    def _kv_section(
        self,
        parent: tk.Widget,
        title: str,
        rows: list[tuple[str, str]],
    ) -> None:
        outer, content = self._make_card(parent, title)
        outer.pack(fill=tk.X, pady=(10, 0))
        for key, label in rows:
            var = tk.StringVar(value="—")
            self._vars[key] = var
            row = tk.Frame(content, bg=_CARD)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label + ":", font=("Segoe UI", 9),
                     fg=_MUTED, bg=_CARD, width=20, anchor="w").pack(side=tk.LEFT)
            lbl = tk.Label(row, textvariable=var, font=("Segoe UI", 9),
                           fg=_TEXT, bg=_CARD, anchor="w", wraplength=320, justify="left")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._value_labels[key] = lbl

    def _make_btn(
        self, parent: tk.Frame, text: str, cmd: Callable[[], None], bg: str
    ) -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Segoe UI", 9, "bold"),
            fg=_WHITE, bg=bg, activeforeground=_WHITE, activebackground=bg,
            relief=tk.FLAT, cursor="hand2", padx=14, pady=6, bd=0,
        )

    def _draw_eye(self, canvas: tk.Canvas, size: int) -> None:
        cx, cy = size // 2, size // 2
        ew, eh = int(size * 0.90), int(size * 0.54)
        ex0, ey0 = cx - ew // 2, cy - eh // 2
        ex1, ey1 = ex0 + ew, ey0 + eh
        canvas.create_oval(ex0, ey0, ex1, ey1, fill="white", outline="#0a4a0a", width=2)
        r = int(size * 0.20)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#196127")
        r = int(size * 0.14)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#3fb950")
        r = int(size * 0.09)
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#0a0a0a")
        hl = int(size * 0.04)
        hx, hy = cx + int(size * 0.07), cy - int(size * 0.07)
        canvas.create_oval(hx - hl, hy - hl, hx + hl, hy + hl, fill="white")

    def _center(self, w: int, h: int) -> None:
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Visibility ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self._visible = True
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()
        self._schedule_refresh()

    def hide(self) -> None:
        self._visible = False
        self._root.withdraw()
        if self._after_id:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ── Refresh loop ──────────────────────────────────────────────────────────

    def _schedule_refresh(self) -> None:
        if self._after_id:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self._root.after(self._REFRESH_MS, self._refresh)

    def _refresh(self) -> None:
        self._after_id = None
        try:
            self._update_ui()
        except Exception as exc:
            LOGGER.debug("GUI refresh error: %s", exc)
        if self._visible:
            self._schedule_refresh()

    def _update_ui(self) -> None:
        snap = self._status.snapshot()
        cfg = self._get_config()

        # ── Status indicator ──────────────────────────────────────────────────
        if self._status_dot is None or self._status_text is None:
            return
        if snap.running:
            self._status_dot.configure(fg=self._theme.palette["green"])
            self._status_text.configure(text="EXECUTANDO", fg=self._theme.palette["green"])
        else:
            self._status_dot.configure(fg=self._theme.palette["red"])
            self._status_text.configure(text="PARADO", fg=self._theme.palette["red"])

        # ── Uptime ────────────────────────────────────────────────────────────
        if snap.started_at is not None:
            elapsed = int((datetime.now(timezone.utc) - snap.started_at).total_seconds())
        else:
            elapsed = snap.uptime_seconds
        h, rem = divmod(max(0, elapsed), 3600)
        m, s = divmod(rem, 60)
        self._uptime_var.set(f"{h:02d}:{m:02d}:{s:02d}")

        # ── Scan ──────────────────────────────────────────────────────────────
        self._set("last_scan", format_timestamp(snap.last_scan) or "—")
        self._set("next_scan", _fmt_next_scan(snap.last_scan, cfg.poll_interval_seconds))
        self._set("last_result", snap.last_scan_result or "—")

        # ── Alerts ────────────────────────────────────────────────────────────
        self._set("last_match", snap.last_match or "—")
        self._set("last_match_at", format_timestamp(snap.last_match_at) or "—")
        last_send_fmt = format_timestamp(snap.last_send)
        self._set("last_send", last_send_fmt or "—")

        # ── Errors ────────────────────────────────────────────────────────────
        self._set("error_count", str(snap.error_count))
        lbl = self._value_labels.get("error_count")
        if lbl:
            lbl.configure(fg=self._theme.palette["red"] if snap.error_count else self._theme.palette["green"])

        self._set("last_error", snap.last_error or "—")
        lbl = self._value_labels.get("last_error")
        if lbl:
            lbl.configure(fg=self._theme.palette["red"] if snap.last_error else self._theme.palette["muted"])

        self._set("breaker_active", str(snap.breaker_active_count))
        lbl = self._value_labels.get("breaker_active")
        if lbl:
            lbl.configure(fg=self._theme.palette["red"] if snap.breaker_active_count else self._theme.palette["text"])

        # ── Email queue ───────────────────────────────────────────────────────
        q = snap.email_queue
        self._set("q_pending", str(q.get("queued", 0)))
        self._set("q_sent", str(q.get("sent", 0)))
        self._set("q_failed", str(q.get("failed", 0)))
        self._set("q_deferred", str(q.get("deferred", 0)))

        # ── Monitors ──────────────────────────────────────────────────────────
        self._update_monitors(snap, cfg)

    def _set(self, key: str, value: str) -> None:
        var = self._vars.get(key)
        if var is not None:
            var.set(value)

    def _update_monitors(self, snap: object, cfg: AppConfig) -> None:
        if self._monitors_content is None:
            return
        for w in self._monitors_content.winfo_children():
            w.destroy()
        if not cfg.monitors:
            p = self._theme.palette
            tk.Label(self._monitors_content, text="Nenhum monitor configurado.",
                     font=("Segoe UI", 9), fg=p["muted"], bg=p["card"]).pack(anchor="w")
            return
        failures = getattr(snap, "monitor_failures", {})
        breakers = getattr(snap, "monitor_breakers_active", {})
        p = self._theme.palette
        for idx, monitor in enumerate(cfg.monitors, start=1):
            key = monitor.window_title_regex or f"monitor_{idx}"
            fail_count = failures.get(key, 0)
            breaker = breakers.get(key, False)
            if breaker:
                dot_fg, note = p["red"], "  [CIRCUITO ABERTO]"
            elif fail_count > 0:
                dot_fg, note = p["amber"], f"  {fail_count} falha(s)"
            else:
                dot_fg, note = p["green"], ""
            row = tk.Frame(self._monitors_content, bg=p["card"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text="●", font=("Segoe UI", 11), fg=dot_fg, bg=p["card"]).pack(
                side=tk.LEFT, padx=(0, 8))
            title = monitor.window_title_regex or f"Monitor {idx}"
            if len(title) > 48:
                title = title[:45] + "..."
            tk.Label(row, text=f"Monitor {idx}:  {title}",
                     font=("Segoe UI", 9), fg=p["text"], bg=p["card"]).pack(side=tk.LEFT)
            if note:
                tk.Label(row, text=note, font=("Segoe UI", 9),
                         fg=p["red"] if breaker else p["amber"], bg=p["card"]).pack(side=tk.LEFT)

    def _trigger_scan(self) -> None:
        self._on_manual_scan()

    def _toggle_theme(self) -> None:
        self._theme.toggle(self._root)
        if self._theme_btn is not None:
            p = self._theme.palette
            label = "☀  Tema Claro" if self._theme.is_dark else "🌙  Tema Escuro"
            self._theme_btn.configure(
                text=label, bg=p["btn_dim"], fg=p["white"],
                activebackground=p["btn_dim"], activeforeground=p["white"],
            )


# ── Module-level helpers ──────────────────────────────────────────────────────

def _fmt_next_scan(last_scan: str, poll_interval_seconds: int) -> str:
    if not last_scan or not poll_interval_seconds:
        return "—"
    try:
        last = datetime.fromisoformat(last_scan)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        remaining = (
            last + timedelta(seconds=poll_interval_seconds) - datetime.now(timezone.utc)
        ).total_seconds()
        if remaining <= 0:
            return "iminente"
        m, s = divmod(int(remaining), 60)
        return f"em {m}m {s:02d}s" if m else f"em {s}s"
    except (ValueError, TypeError):
        return "—"


def _start_notifier(
    config: AppConfig,
    status: StatusStore,
    stop_event: Event,
    manual_scan_event: Event,
    scan_complete_event: Event | None = None,
    test_message_event: Event | None = None,
) -> Thread:
    notifier = Notifier(config=config, status=status)
    t = Thread(
        target=notifier.run_loop,
        args=(stop_event, manual_scan_event, scan_complete_event, test_message_event),
        daemon=True,
    )
    t.start()
    return t


# ── Main entry point ──────────────────────────────────────────────────────────

def run_gui(config: AppConfig, *, smtp_validator=None) -> None:
    """GUI entry point — opens the status window on startup."""
    set_console_visible(False)

    status = StatusStore()
    manual_scan_event = Event()
    scan_complete_event = Event()
    test_message_event = Event()
    exit_event = Event()

    stop_holder: list[Event] = [Event()]
    thread_holder: list[Thread] = [
        _start_notifier(
            config, status, stop_holder[0],
            manual_scan_event, scan_complete_event, test_message_event,
        )
    ]
    config_holder: list[AppConfig] = [config]

    # ── Tk root ───────────────────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()

    # ── Theme state ───────────────────────────────────────────────────────────
    theme = _ThemeState()

    # ── Config editor ─────────────────────────────────────────────────────────
    def _reload_notifier(new_cfg: AppConfig) -> None:
        old_stop = stop_holder[0]
        old_stop.set()
        try:
            thread_holder[0].join(timeout=5)
        except Exception:
            pass
        new_stop = Event()
        stop_holder[0] = new_stop
        status.set_last_error("")
        thread_holder[0] = _start_notifier(
            new_cfg, status, new_stop,
            manual_scan_event, scan_complete_event, test_message_event,
        )
        config_holder[0] = new_cfg

    editor = ConfigEditorWindow(root, on_saved=_reload_notifier, theme_state=theme)

    def open_config() -> None:
        root.after(0, editor.show)

    # ── Status window ─────────────────────────────────────────────────────────
    window = StatusWindow(
        root,
        status,
        config,
        get_config=lambda: config_holder[0],
        on_manual_scan=manual_scan_event.set,
        on_open_config=open_config,
        on_exit=exit_event.set,
        theme_state=theme,
    )

    # ── Tray icon ─────────────────────────────────────────────────────────────
    def _show_from_tray() -> None:
        root.after(0, window.show)

    tray = TrayIcon(
        on_exit_requested=exit_event.set,
        on_open_status=_show_from_tray,
    )
    tray.start()

    # ── Show window on startup ────────────────────────────────────────────────
    root.after(0, window.show)

    # ── Watchdog thread ───────────────────────────────────────────────────────
    def _watchdog() -> None:
        while not exit_event.wait(5):
            if not thread_holder[0].is_alive() and not stop_holder[0].is_set():
                LOGGER.warning("Notifier died; restarting", extra={"category": "startup"})
                _reload_notifier(config_holder[0])

    Thread(target=_watchdog, daemon=True, name="gui-watchdog").start()

    # ── Exit poller ───────────────────────────────────────────────────────────
    def _check_exit() -> None:
        if exit_event.is_set():
            stop_holder[0].set()
            tray.stop()
            try:
                root.quit()
            except Exception:
                pass
            return
        root.after(300, _check_exit)

    root.after(300, _check_exit)

    # ── Run mainloop ──────────────────────────────────────────────────────────
    try:
        root.mainloop()
    except Exception as exc:
        LOGGER.error("GUI mainloop error: %s", exc, extra={"category": "startup"})
    finally:
        stop_holder[0].set()
        tray.stop()
