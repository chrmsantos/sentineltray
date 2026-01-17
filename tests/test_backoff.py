from sentineltray.app import Notifier
from sentineltray.config import AppConfig, WhatsappConfig
from sentineltray.status import StatusStore


def test_compute_backoff_seconds_caps() -> None:
    config = AppConfig(
        window_title_regex="APP",
        phrase_regex="ALERT",
        poll_interval_seconds=1,
        healthcheck_interval_seconds=3600,
        error_backoff_base_seconds=5,
        error_backoff_max_seconds=20,
        debounce_seconds=600,
        max_history=10,
        state_file="state.json",
        log_file="logs/sentineltray.log",
        telemetry_file="logs/telemetry.json",
        whatsapp=WhatsappConfig(
            mode="web",
            chat_target="Operator",
            user_data_dir="session",
            timeout_seconds=10,
            dry_run=True,
        ),
    )
    notifier = Notifier(config=config, status=StatusStore())

    assert notifier._compute_backoff_seconds(0) == 0
    assert notifier._compute_backoff_seconds(1) == 5
    assert notifier._compute_backoff_seconds(2) == 10
    assert notifier._compute_backoff_seconds(3) == 20
    assert notifier._compute_backoff_seconds(4) == 20
