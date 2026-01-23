import json
import logging
import os
import platform
import re
import sys
import threading
import time
import warnings
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path, PureWindowsPath
from uuid import uuid4

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


class ContextFilter(logging.Filter):
    def __init__(self, *, session_id: str, app_version: str, release_date: str, commit_hash: str) -> None:
        super().__init__()
        self._session_id = session_id
        self._app_version = app_version
        self._release_date = release_date
        self._commit_hash = commit_hash
        self._hostname = platform.node()
        self._platform = platform.platform()
        self._python = platform.python_version()
        self._pid = os.getpid()
        self._process_start = time.time()

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "session_id"):
            record.session_id = self._session_id
        if not hasattr(record, "app_version"):
            record.app_version = self._app_version
        if not hasattr(record, "release_date"):
            record.release_date = self._release_date
        if not hasattr(record, "commit_hash"):
            record.commit_hash = self._commit_hash
        if not hasattr(record, "hostname"):
            record.hostname = self._hostname
        if not hasattr(record, "platform"):
            record.platform = self._platform
        if not hasattr(record, "python_version"):
            record.python_version = self._python
        if not hasattr(record, "pid"):
            record.pid = self._pid
        if not hasattr(record, "uptime_seconds"):
            record.uptime_seconds = max(0.0, time.time() - self._process_start)
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


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = sanitize_text(record.getMessage())
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "category": getattr(record, "category", "general"),
            "logger": record.name,
            "message": message,
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "process": record.process,
            "process_name": record.processName,
            "thread": record.thread,
            "thread_name": record.threadName,
            "session_id": getattr(record, "session_id", ""),
            "app_version": getattr(record, "app_version", ""),
            "release_date": getattr(record, "release_date", ""),
            "commit_hash": getattr(record, "commit_hash", ""),
            "hostname": getattr(record, "hostname", ""),
            "platform": getattr(record, "platform", ""),
            "python_version": getattr(record, "python_version", ""),
            "pid": getattr(record, "pid", record.process),
            "uptime_seconds": round(getattr(record, "uptime_seconds", 0.0), 3),
        }
        if record.exc_info:
            payload["exception"] = sanitize_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def _install_exception_hooks() -> None:
    logger = logging.getLogger(__name__)

    def handle_exception(exc_type, exc, tb) -> None:
        if exc_type in (KeyboardInterrupt, SystemExit):
            logger.info(
                "Shutdown requested",
                extra={"category": "shutdown"},
            )
            return
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc, tb),
            extra={"category": "fatal"},
        )

    sys.excepthook = handle_exception

    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
            if args.exc_type in (KeyboardInterrupt, SystemExit):
                logger.info(
                    "Thread shutdown requested",
                    extra={"category": "shutdown"},
                )
                return
            logger.critical(
                "Unhandled thread exception",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                extra={"category": "fatal"},
            )

        threading.excepthook = _thread_excepthook


def _build_run_log_path(base_path: Path, *, suffix: str | None = None) -> Path:
    if suffix:
        base_path = base_path.with_suffix(suffix)
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
    app_version: str | None = None,
    release_date: str | None = None,
    commit_hash: str | None = None,
) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            try:
                handler.close()
            finally:
                root_logger.removeHandler(handler)
    base_path = Path(log_file)
    if not base_path.suffix:
        base_path = base_path.with_suffix(".log")
    base_path.parent.mkdir(parents=True, exist_ok=True)
    run_path = _build_run_log_path(base_path)
    json_base_path = base_path.with_suffix(".jsonl")
    json_run_path = _build_run_log_path(base_path, suffix=".jsonl")

    session_id = uuid4().hex
    context_filter = ContextFilter(
        session_id=session_id,
        app_version=str(app_version or ""),
        release_date=str(release_date or ""),
        commit_hash=str(commit_hash or ""),
    )

    formatter = SanitizingFormatter(
        "%(asctime)s %(levelname)s %(category)s %(name)s %(filename)s:%(lineno)d "
        "%(funcName)s %(process)d %(processName)s %(thread)d %(threadName)s %(message)s"
    )
    json_formatter = JsonFormatter()

    resolved_level = _resolve_level(log_level, logging.INFO)
    resolved_console_level = _resolve_level(log_console_level, logging.WARNING)

    effective_backup_count = min(MAX_LOG_FILES, max(0, log_backup_count))
    effective_run_files_keep = min(MAX_LOG_FILES, max(1, log_run_files_keep))

    handlers: list[logging.Handler] = []

    try:
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
        rotating_handler.addFilter(context_filter)
        handlers.append(rotating_handler)

        run_handler = logging.FileHandler(run_path, encoding="utf-8")
        run_handler.setFormatter(formatter)
        run_handler.setLevel(resolved_level)
        run_handler.addFilter(CategoryFilter())
        run_handler.addFilter(RedactionFilter())
        run_handler.addFilter(context_filter)
        handlers.append(run_handler)

        json_handler = RotatingFileHandler(
            json_base_path,
            maxBytes=log_max_bytes,
            backupCount=effective_backup_count,
            encoding="utf-8",
        )
        json_handler.setFormatter(json_formatter)
        json_handler.setLevel(resolved_level)
        json_handler.addFilter(CategoryFilter())
        json_handler.addFilter(RedactionFilter())
        json_handler.addFilter(context_filter)
        handlers.append(json_handler)

        json_run_handler = logging.FileHandler(json_run_path, encoding="utf-8")
        json_run_handler.setFormatter(json_formatter)
        json_run_handler.setLevel(resolved_level)
        json_run_handler.addFilter(CategoryFilter())
        json_run_handler.addFilter(RedactionFilter())
        json_run_handler.addFilter(context_filter)
        handlers.append(json_run_handler)
    except OSError as exc:
        fallback = logging.StreamHandler()
        fallback.setFormatter(formatter)
        fallback.setLevel(resolved_level)
        fallback.addFilter(CategoryFilter())
        fallback.addFilter(RedactionFilter())
        fallback.addFilter(context_filter)
        handlers.append(fallback)
        logging.getLogger(__name__).warning(
            "Failed to initialize file logging: %s",
            exc,
            extra={"category": "startup"},
        )

    if log_console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(resolved_console_level)
        console_handler.addFilter(CategoryFilter())
        console_handler.addFilter(RedactionFilter())
        console_handler.addFilter(context_filter)
        handlers.append(console_handler)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)

    warnings.simplefilter("default")
    logging.captureWarnings(True)
    _install_exception_hooks()

    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("PIL.Image").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialized",
        extra={
            "category": "startup",
            "log_file": str(base_path),
            "run_log_file": str(run_path),
            "json_log_file": str(json_base_path),
            "json_run_log_file": str(json_run_path),
            "session_id": session_id,
        },
    )
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

    _cleanup_old_logs(
        json_run_path.parent,
        json_base_path.stem,
        json_base_path.suffix,
        keep=effective_run_files_keep,
    )
