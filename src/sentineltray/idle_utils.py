from __future__ import annotations

import sys


def get_idle_seconds() -> float:
    """Return seconds elapsed since the last keyboard or mouse input.

    Uses GetLastInputInfo on Windows.  Returns ``float('inf')`` on
    non-Windows platforms or when the Win32 call fails, so callers that
    compare against a threshold will never pause on unsupported platforms.
    """
    if sys.platform != "win32":
        return float("inf")

    import ctypes
    import ctypes.wintypes

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):  # type: ignore[attr-defined]
        return float("inf")

    # GetTickCount wraps at ~49.7 days; mask to uint32 to handle the rollover
    tick_count: int = ctypes.windll.kernel32.GetTickCount()  # type: ignore[attr-defined]
    idle_ms = (tick_count - lii.dwTime) & 0xFFFFFFFF
    return idle_ms / 1000.0
