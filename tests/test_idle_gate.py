import sentineltray.app as app


def test_is_user_idle_true(monkeypatch) -> None:
    monkeypatch.setattr(app, "_get_idle_seconds", lambda: 125.0)
    assert app._is_user_idle(120) is True


def test_is_user_idle_false(monkeypatch) -> None:
    monkeypatch.setattr(app, "_get_idle_seconds", lambda: 45.0)
    assert app._is_user_idle(120) is False
