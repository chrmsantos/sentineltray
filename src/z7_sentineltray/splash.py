"""Minimal splash screen shown while the application initializes.

Runs in a daemon background thread with its own Tcl/Tk interpreter so that
the main thread is never blocked and the window appears almost instantly,
before any file I/O or config loading takes place.
"""

from __future__ import annotations

import contextlib
import threading


class SplashScreen:
    """Borderless loading window rendered in a background thread.

    The window appears almost instantly and closes when :meth:`close` is
    called.  :meth:`close` is idempotent and safe to call from any thread.

    Example usage::

        splash = SplashScreen()
        # ... do heavy startup work ...
        splash.close()
    """

    _BG = "#0d1117"
    _GREEN = "#3fb950"
    _TEXT = "#c9d1d9"
    _MUTED = "#8b949e"
    _BORDER = "#30363d"
    _WIDTH = 340
    _HEIGHT = 160

    def __init__(self) -> None:
        self._ready = threading.Event()
        self._close = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="splash-screen"
        )
        self._thread.start()
        # Block until the window is actually on screen (or the thread fails).
        self._ready.wait(timeout=2)

    def _run(self) -> None:  # noqa: C901
        try:
            import tkinter as tk
        except Exception:
            self._ready.set()
            return

        _root: tk.Tk | None = None
        _dot_var: tk.StringVar | None = None

        try:
            _root = tk.Tk()
            _root.configure(bg=self._BG)
            _root.title("Z7_SentinelTray")
            _root.resizable(False, False)
            _root.overrideredirect(True)

            w, h = self._WIDTH, self._HEIGHT
            sw = _root.winfo_screenwidth()
            sh = _root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            _root.geometry(f"{w}x{h}+{x}+{y}")

            # 1-pixel border via outer frame
            outer = tk.Frame(_root, bg=self._BORDER)
            outer.place(x=0, y=0, width=w, height=h)

            inner = tk.Frame(outer, bg=self._BG)
            inner.place(x=1, y=1, width=w - 2, height=h - 2)

            tk.Label(
                inner,
                text="Z7 SentinelTray",
                font=("Segoe UI", 16, "bold"),
                fg=self._GREEN,
                bg=self._BG,
            ).place(relx=0.5, y=52, anchor="center")

            tk.Label(
                inner,
                text="Monitor de janelas",
                font=("Segoe UI", 9),
                fg=self._MUTED,
                bg=self._BG,
            ).place(relx=0.5, y=80, anchor="center")

            _label_dot = tk.Label(
                inner,
                text="Iniciando   ",
                font=("Segoe UI", 9),
                fg=self._TEXT,
                bg=self._BG,
            )
            _label_dot.place(relx=0.5, y=112, anchor="center")

            _root.lift()
            _root.attributes("-topmost", True)
            _root.update()
            # Release topmost after a short delay so it doesn't sit above
            # subsequent dialogs (password prompt, config editor, etc.).
            _root.after(300, lambda: _root.attributes("-topmost", False))  # type: ignore[union-attr]
        except Exception:
            self._ready.set()
            if _root is not None:
                with contextlib.suppress(Exception):
                    _root.destroy()
            return

        self._ready.set()

        # Create non-optional local aliases for the type checker.
        root_nn: tk.Tk = _root  # type: ignore[assignment]
        label_dot_nn: tk.Label = _label_dot  # type: ignore[assignment]
        tick_count = [0]

        def _tick() -> None:
            if self._close.is_set():
                with contextlib.suppress(Exception):
                    root_nn.quit()
                return
            tick_count[0] += 1
            # Advance dot animation every 8 ticks × 50 ms = 400 ms
            if tick_count[0] % 8 == 0:
                phase = (tick_count[0] // 8) % 4
                label_dot_nn.configure(text="Iniciando" + ("." * phase).ljust(3))
            root_nn.after(50, _tick)

        root_nn.after(0, _tick)
        try:
            root_nn.mainloop()
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                root_nn.destroy()

    def close(self) -> None:
        """Signal the splash to close and wait for the thread to exit.

        Waits for the background Tcl/Tk interpreter to be fully destroyed before
        returning, so it is safe to create a new ``tk.Tk()`` in the main thread
        immediately after this call returns.  Safe to call multiple times from
        any thread.
        """
        self._close.set()
        self._thread.join(timeout=3)
