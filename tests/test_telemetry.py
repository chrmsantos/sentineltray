import json
from pathlib import Path

from sentineltray.telemetry import TelemetryWriter


def test_telemetry_writer_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.json"
    writer = TelemetryWriter(path)

    payload = {
        "updated_at": "t1",
        "running": True,
        "uptime_seconds": 1,
        "last_scan": "s1",
        "last_match": "m1",
        "last_send": "send1",
        "last_error": "",
        "last_healthcheck": "h1",
        "error_count": 0,
    }

    writer.write(payload)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["updated_at"] == "t1"
    assert data["running"] is True
    assert data["error_count"] == 0
