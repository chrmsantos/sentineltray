import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class CategoryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "category"):
            record.category = "general"
        return True


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

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(category)s %(name)s %(filename)s:%(lineno)d "
        "%(funcName)s %(process)d %(threadName)s %(message)s"
    )

    resolved_level = _resolve_level(log_level, logging.INFO)
    resolved_console_level = _resolve_level(log_console_level, logging.WARNING)

    rotating_handler = RotatingFileHandler(
        base_path,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    rotating_handler.setFormatter(formatter)
    rotating_handler.setLevel(resolved_level)
    rotating_handler.addFilter(CategoryFilter())

    run_handler = logging.FileHandler(run_path, encoding="utf-8")
    run_handler.setFormatter(formatter)
    run_handler.setLevel(resolved_level)
    run_handler.addFilter(CategoryFilter())

    handlers = [rotating_handler, run_handler]

    if log_console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(resolved_console_level)
        console_handler.addFilter(CategoryFilter())
        handlers.append(console_handler)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)

    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("PIL.Image").setLevel(logging.WARNING)
    _cleanup_old_logs(run_path.parent, base_path.stem, base_path.suffix, keep=log_run_files_keep)
