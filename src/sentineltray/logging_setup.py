import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path, PureWindowsPath

MAX_LOG_FILES = 5

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s]+")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s\-()]{7,}\d)\b")
TOKEN_RE = re.compile(
    r"(?i)\b(bearer|token|apikey|api_key|secret|password)\s*[:=]\s*[^\s,;]+"
)


class CategoryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "category"):
            record.category = "general"
        return True


def _redact_windows_path(match: re.Match[str]) -> str:
    raw = match.group(0)
    tail = PureWindowsPath(raw).name
    drive = raw[:2]
    if tail:
        return f"{drive}\\...\\{tail}"
    return f"{drive}\\..."


def sanitize_text(value: str) -> str:
    if not value:
        return value
    sanitized = EMAIL_RE.sub("<email>", value)
    sanitized = WINDOWS_PATH_RE.sub(_redact_windows_path, sanitized)
    sanitized = PHONE_RE.sub("<phone>", sanitized)
    sanitized = TOKEN_RE.sub(r"\1=<redacted>", sanitized)
    return sanitized


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = sanitize_text(record.getMessage())
        record.msg = message
        record.args = ()
        return True


class SanitizingFormatter(logging.Formatter):
    def formatException(self, ei) -> str:
        return sanitize_text(super().formatException(ei))


def _build_run_log_path(log_file: str) -> Path:
    base_path = Path(log_file)
    if not base_path.suffix:
        base_path = base_path.with_suffix(".log")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_path.stem}_{timestamp}_{os.getpid()}{base_path.suffix}"
    return base_path.parent / filename


def _cleanup_old_logs(log_dir: Path, stem: str, suffix: str, keep: int) -> None:
    candidates = sorted(
        log_dir.glob(f"{stem}_*{suffix}"),
        key=lambda path: path.stat().st_mtime,
    )
    if len(candidates) <= keep:
        return
    for path in candidates[: len(candidates) - keep]:
        try:
            path.unlink()
        except OSError:
            continue


def _resolve_level(level: str, default: int) -> int:
    name = str(level).upper()
    return logging._nameToLevel.get(name, default)


def setup_logging(
    log_file: str,
    *,
    log_level: str = "INFO",
    log_console_level: str = "WARNING",
    log_console_enabled: bool = True,
    log_max_bytes: int = 5_000_000,
    log_backup_count: int = 5,
    log_run_files_keep: int = 5,
) -> None:
    base_path = Path(log_file)
    if not base_path.suffix:
        base_path = base_path.with_suffix(".log")
    base_path.parent.mkdir(parents=True, exist_ok=True)
    run_path = _build_run_log_path(str(base_path))

    formatter = SanitizingFormatter(
        "%(asctime)s %(levelname)s %(category)s %(name)s %(filename)s:%(lineno)d "
        "%(funcName)s %(process)d %(threadName)s %(message)s"
    )

    resolved_level = _resolve_level(log_level, logging.INFO)
    resolved_console_level = _resolve_level(log_console_level, logging.WARNING)

    effective_backup_count = min(MAX_LOG_FILES, max(0, log_backup_count))
    effective_run_files_keep = min(MAX_LOG_FILES, max(1, log_run_files_keep))

    rotating_handler = RotatingFileHandler(
        base_path,
        maxBytes=log_max_bytes,
        backupCount=effective_backup_count,
        encoding="utf-8",
    )
    rotating_handler.setFormatter(formatter)
    rotating_handler.setLevel(resolved_level)
    rotating_handler.addFilter(CategoryFilter())
    rotating_handler.addFilter(RedactionFilter())

    run_handler = logging.FileHandler(run_path, encoding="utf-8")
    run_handler.setFormatter(formatter)
    run_handler.setLevel(resolved_level)
    run_handler.addFilter(CategoryFilter())
    run_handler.addFilter(RedactionFilter())

    handlers = [rotating_handler, run_handler]

    if log_console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(resolved_console_level)
        console_handler.addFilter(CategoryFilter())
        console_handler.addFilter(RedactionFilter())
        handlers.append(console_handler)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)

    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("PIL.Image").setLevel(logging.WARNING)
    if effective_backup_count != log_backup_count:
        logging.getLogger(__name__).warning(
            "log_backup_count capped at %s (requested %s)",
            MAX_LOG_FILES,
            log_backup_count,
        )
    if effective_run_files_keep != log_run_files_keep:
        logging.getLogger(__name__).warning(
            "log_run_files_keep capped at %s (requested %s)",
            MAX_LOG_FILES,
            log_run_files_keep,
        )

    _cleanup_old_logs(
        run_path.parent,
        base_path.stem,
        base_path.suffix,
        keep=effective_run_files_keep,
    )
