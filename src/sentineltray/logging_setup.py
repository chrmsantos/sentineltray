import logging
import os
from datetime import datetime
from pathlib import Path


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


def setup_logging(log_file: str) -> None:
    base_path = Path(log_file)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    run_path = _build_run_log_path(log_file)

    handler = logging.FileHandler(run_path, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d "
        "%(funcName)s %(process)d %(threadName)s %(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(handler)

    _cleanup_old_logs(run_path.parent, base_path.stem, base_path.suffix, keep=5)
