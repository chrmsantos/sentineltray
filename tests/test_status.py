from sentineltray.status import StatusStore, format_status


def test_status_store_snapshot() -> None:
    store = StatusStore()
    store.set_running(True)
    store.set_paused(True)
    store.set_last_scan("t1")
    store.set_last_match("m1")
    store.set_last_send("s1")
    store.set_last_error("e1")
    store.set_last_healthcheck("h1")
    store.set_uptime_seconds(42)
    store.increment_error_count()
    store.increment_error_count()

    snapshot = store.snapshot()
    assert snapshot.running is True
    assert snapshot.paused is True
    assert snapshot.last_scan == "t1"
    assert snapshot.last_match == "m1"
    assert snapshot.last_send == "s1"
    assert snapshot.last_error == "e1"
    assert snapshot.last_healthcheck == "h1"
    assert snapshot.uptime_seconds == 42
    assert snapshot.error_count == 2

    text = format_status(snapshot)
    assert "Em execução: sim" in text
    assert "Pausado: sim" in text
