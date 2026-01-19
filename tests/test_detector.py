from pywinauto.findwindows import ElementAmbiguousError

from sentineltray.detector import WindowTextDetector


def test_prepare_window_restores_minimized(monkeypatch) -> None:
    calls: list[str] = []

    class FakeWindow:
        def exists(self, timeout: int = 0) -> bool:
            return True

        def is_minimized(self) -> bool:
            return True

        def is_maximized(self) -> bool:
            return False

        def restore(self) -> None:
            calls.append("restore")

        def maximize(self) -> None:
            calls.append("maximize")

        def minimize(self) -> None:
            calls.append("minimize")

        def set_focus(self) -> None:
            calls.append("focus")

        def wait(self, *_args, **_kwargs) -> None:
            return None

        def is_enabled(self) -> bool:
            return True

        def descendants(self):
            return []

    detector = WindowTextDetector("APP", allow_window_restore=True)
    monkeypatch.setattr(detector, "_get_window", lambda: FakeWindow())

    detector.find_matches("ALERT")

    assert "restore" in calls
    assert "focus" in calls
    assert "maximize" in calls
    assert "minimize" in calls


def test_find_matches_accent_insensitive(monkeypatch) -> None:
    detector = WindowTextDetector("APP", allow_window_restore=True)
    monkeypatch.setattr(
        detector,
        "_iter_texts",
        lambda: ["Sessão encerrada", "Ação confirmada", "Sem alerta"],
    )

    assert detector.find_matches("Sessao") == ["Sessão encerrada"]
    assert detector.find_matches("Acao") == ["Ação confirmada"]


def test_find_matches_partial_text(monkeypatch) -> None:
    detector = WindowTextDetector("APP", allow_window_restore=True)
    monkeypatch.setattr(
        detector,
        "_iter_texts",
        lambda: ["Erro no sistema principal", "Tudo certo"],
    )

    assert detector.find_matches("Erro") == ["Erro no sistema principal"]


def test_find_matches_case_insensitive(monkeypatch) -> None:
    detector = WindowTextDetector("APP", allow_window_restore=True)
    monkeypatch.setattr(
        detector,
        "_iter_texts",
        lambda: ["Processo concluído", "Alerta crítico"],
    )

    assert detector.find_matches("alerta") == ["Alerta crítico"]


def test_get_window_resolves_ambiguous(monkeypatch) -> None:
    class FakeWindow:
        def __init__(self, focus: bool, visible: bool, enabled: bool) -> None:
            self._focus = focus
            self._visible = visible
            self._enabled = enabled

        def has_focus(self) -> bool:
            return self._focus

        def is_visible(self) -> bool:
            return self._visible

        def is_enabled(self) -> bool:
            return self._enabled

    class FakeSpec:
        def wrapper_object(self):
            raise ElementAmbiguousError("ambiguous")

    class FakeDesktop:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def window(self, *_args, **_kwargs):
            return FakeSpec()

        def windows(self, *_args, **_kwargs):
            return [
                FakeWindow(False, True, True),
                FakeWindow(True, True, True),
            ]

    detector = WindowTextDetector("APP", allow_window_restore=True)
    monkeypatch.setattr("sentineltray.detector.Desktop", FakeDesktop)

    window = detector._get_window()

    assert isinstance(window, FakeWindow)
    assert window.has_focus()
