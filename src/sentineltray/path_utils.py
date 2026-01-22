from __future__ import annotations

from pathlib import Path


def resolve_sensitive_path(base: Path, value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return str(base / candidate)
    try:
        if candidate.resolve().is_relative_to(base.resolve()):
            return str(candidate)
    except OSError:
        pass
    return str(base / candidate.name)


def resolve_log_path(base: Path, log_root: Path, value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return str(base / candidate)
    try:
        if candidate.resolve().is_relative_to(log_root.resolve()):
            return str(candidate)
    except OSError:
        pass
    return str(log_root / candidate.name)


def ensure_under_root(log_root: Path, path_value: str, label: str) -> None:
    try:
        resolved = Path(path_value).resolve()
        if not resolved.is_relative_to(log_root):
            raise ValueError(f"{label} must be under {log_root}")
    except OSError as exc:
        raise ValueError(f"{label} must be under {log_root}") from exc
