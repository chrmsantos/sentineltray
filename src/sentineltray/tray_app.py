from __future__ import annotations

import logging
import os
import subprocess
import sys
from threading import Event, Thread

from PIL import Image, ImageDraw
import pystray

from .app import Notifier
from .config import AppConfig, get_project_root
from .status import StatusStore

LOGGER = logging.getLogger(__name__)


def _build_tray_image() -> Image.Image:
	image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
	draw = ImageDraw.Draw(image)
	draw.ellipse((12, 12, 52, 52), fill=(60, 200, 80), outline=(255, 255, 255), width=3)
	return image


def _start_notifier(
	config: AppConfig,
	status: StatusStore,
	stop_event: Event,
	pause_event: Event,
	manual_scan_event: Event,
) -> Thread:
	notifier = Notifier(config=config, status=status)
	thread = Thread(
		target=notifier.run_loop,
		args=(stop_event, pause_event, manual_scan_event),
		daemon=True,
	)
	thread.start()
	return thread


def _open_cli_terminal() -> None:
	try:
		root = get_project_root()
		cli_entry = root / "cli.py"
		command = f"{sys.executable} {cli_entry}"
		env = os.environ.copy()
		env.setdefault("SENTINELTRAY_ROOT", str(root))
		subprocess.Popen(
			[
				"cmd",
				"/c",
				"start",
				"",
				str(sys.executable),
				str(cli_entry),
			],
			env=env,
		)
	except Exception as exc:
		LOGGER.warning("Failed to open CLI terminal: %s", exc)


def run_tray(config: AppConfig) -> None:
	status = StatusStore()
	stop_event = Event()
	pause_event = Event()
	manual_scan_event = Event()
	notifier_thread = _start_notifier(
		config, status, stop_event, pause_event, manual_scan_event
	)

	icon = pystray.Icon(
		"sentineltray",
		_build_tray_image(),
		"SentinelTray (Running)",
	)

	def on_open(_: pystray.Icon, __: pystray.MenuItem) -> None:
		_open_cli_terminal()

	def on_exit(_: pystray.Icon, __: pystray.MenuItem) -> None:
		stop_event.set()
		icon.stop()

	icon.menu = pystray.Menu(
		pystray.MenuItem("Open", on_open, default=True),
		pystray.MenuItem("Exit", on_exit),
	)
	try:
		icon.run_detached()
		while not stop_event.is_set():
			stop_event.wait(0.5)
	except Exception as exc:
		LOGGER.error("Tray icon failed: %s", exc)
	finally:
		stop_event.set()
		try:
			icon.stop()
		except Exception:
			pass
		notifier_thread.join(timeout=5)
