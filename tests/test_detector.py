from sentineltray.detector import WindowTextDetector


def test_prepare_window_restores_minimized(monkeypatch) -> None:
    calls: list[str] = []

    class FakeWindow:
        def exists(self, timeout: int = 0) -> bool:
            return True

        def is_minimized(self) -> bool:
            return True

        def restore(self) -> None:
            calls.append("restore")

        def set_focus(self) -> None:
            calls.append("focus")

        def wait(self, *_args, **_kwargs) -> None:
            return None

        def is_enabled(self) -> bool:
            return True

        def descendants(self):
            return []

    detector = WindowTextDetector("APP")
    monkeypatch.setattr(detector, "_get_window", lambda: FakeWindow())

    detector.find_matches("ALERT")

    assert "restore" in calls
    assert "focus" in calls
