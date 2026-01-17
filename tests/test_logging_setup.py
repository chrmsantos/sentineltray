import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from sentineltray.logging_setup import setup_logging


def test_setup_logging_creates_run_log_and_prunes(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    base_log = log_dir / "sentineltray.log"

    existing = []
    for idx in range(6):
        path = log_dir / f"sentineltray_20260101_00000{idx}_123.log"
        path.write_text("old", encoding="utf-8")
        os.utime(path, (1, 1))
        existing.append(path)

    setup_logging(str(base_log))

    logs = sorted(log_dir.glob("sentineltray_*.log"))
    assert len(logs) == 5
    assert any(path not in existing for path in logs)
    assert base_log.exists()
    assert logging.getLogger("PIL").level == logging.WARNING
    assert logging.getLogger("PIL.Image").level == logging.WARNING

    handlers = logging.getLogger().handlers
    assert any(isinstance(handler, RotatingFileHandler) for handler in handlers)

    for handler in logging.getLogger().handlers:
        handler.close()
