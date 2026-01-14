from sentineltray.status import StatusStore, format_status


def test_status_store_snapshot() -> None:
    store = StatusStore()
    store.set_running(True)
    store.set_last_scan("t1")
    store.set_last_match("m1")
    store.set_last_send("s1")
    store.set_last_error("e1")

    snapshot = store.snapshot()
    assert snapshot.running is True
    assert snapshot.last_scan == "t1"
    assert snapshot.last_match == "m1"
    assert snapshot.last_send == "s1"
    assert snapshot.last_error == "e1"

    text = format_status(snapshot)
    assert "running: yes" in text
