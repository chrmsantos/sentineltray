"""Tray application tests."""

from __future__ import annotations

from types import SimpleNamespace

from sentineltray import tray_app


class DummyEvent:
	def __init__(self) -> None:
		self._set = False
		self._wait_calls = 0

	def set(self) -> None:
		self._set = True

	def is_set(self) -> bool:
		return self._set

	def wait(self, _: float | None = None) -> bool:
		self._wait_calls += 1
		if self._wait_calls >= 1:
			self._set = True
		return self._set


class DummyThread:
	def __init__(self) -> None:
		self.join_called = False

	def join(self, timeout: float | None = None) -> None:
		self.join_called = True

	def is_alive(self) -> bool:
		return False


class DummyIcon:
	def __init__(self, name: str, image: object, title: str) -> None:
		self.name = name
		self.image = image
		self.title = title
		self.menu = None
		self.run_called = False
		self.run_detached_called = False
		self.stopped = False

	def run(self, setup=None) -> None:
		self.run_called = True
		if setup is not None:
			setup(self)

	def run_detached(self) -> None:
		self.run_detached_called = True

	def stop(self) -> None:
		self.stopped = True


def _build_dummy_pystray(created_icons: list[DummyIcon]) -> SimpleNamespace:
	def icon_factory(name: str, image: object, title: str) -> DummyIcon:
		icon = DummyIcon(name, image, title)
		created_icons.append(icon)
		return icon

	return SimpleNamespace(
		Icon=icon_factory,
		Menu=lambda *items: ("menu", items),
		MenuItem=lambda label, action: ("item", label, action),
	)


def test_run_tray_windows_uses_blocking_run(monkeypatch) -> None:
	created_icons: list[DummyIcon] = []
	pystray_stub = _build_dummy_pystray(created_icons)
	status_started = {"called": False}

	monkeypatch.setattr(tray_app, "pystray", pystray_stub)
	monkeypatch.setattr(tray_app, "Event", DummyEvent)
	monkeypatch.setattr(tray_app, "_build_tray_image", lambda: object())
	monkeypatch.setattr(tray_app, "_start_notifier", lambda *args, **kwargs: DummyThread())
	monkeypatch.setattr(
		tray_app,
		"_start_status_loop_thread",
		lambda *args, **kwargs: status_started.__setitem__("called", True) or DummyThread(),
	)
	monkeypatch.setattr(tray_app.os, "name", "nt", raising=False)

	tray_app.run_tray(SimpleNamespace())

	assert created_icons
	icon = created_icons[0]
	assert icon.run_called is True
	assert icon.run_detached_called is False
	assert status_started["called"] is True


def test_run_tray_non_windows_uses_detached(monkeypatch) -> None:
	created_icons: list[DummyIcon] = []
	pystray_stub = _build_dummy_pystray(created_icons)
	status_started = {"called": False}

	monkeypatch.setattr(tray_app, "pystray", pystray_stub)
	monkeypatch.setattr(tray_app, "Event", DummyEvent)
	monkeypatch.setattr(tray_app, "_build_tray_image", lambda: object())
	monkeypatch.setattr(tray_app, "_start_notifier", lambda *args, **kwargs: DummyThread())
	monkeypatch.setattr(
		tray_app,
		"_start_status_loop_thread",
		lambda *args, **kwargs: status_started.__setitem__("called", True) or DummyThread(),
	)
	monkeypatch.setattr(tray_app.os, "name", "posix", raising=False)

	tray_app.run_tray(SimpleNamespace())

	assert created_icons
	icon = created_icons[0]
	assert icon.run_called is False
	assert icon.run_detached_called is True
	assert status_started["called"] is True
