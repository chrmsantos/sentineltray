from __future__ import annotations

import logging
import os
import subprocess
import sys
from threading import Event, Thread

try:
	from PIL import Image, ImageDraw
	import pystray
	_TRAY_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - optional dependency
	Image = None  # type: ignore[assignment]
	ImageDraw = None  # type: ignore[assignment]
	pystray = None  # type: ignore[assignment]
	_TRAY_IMPORT_ERROR = exc

from .app import Notifier
from .config import (
	AppConfig,
	decrypt_config_payload,
	encrypt_config_text,
	get_encrypted_config_path,
	get_user_data_dir,
	load_config,
)
from .security_utils import parse_payload
from .status import StatusStore

LOGGER = logging.getLogger(__name__)


def _build_tray_image() -> Image.Image:
	if Image is None or ImageDraw is None:
		raise RuntimeError(
			"Tray dependencies missing (Pillow). Install requirements.txt."
		) from _TRAY_IMPORT_ERROR
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


def run_tray(config: AppConfig) -> None:
	if pystray is None:
		raise RuntimeError(
			"Tray dependencies missing (pystray/Pillow). Install requirements.txt."
		) from _TRAY_IMPORT_ERROR
	LOGGER.info("Tray starting", extra={"category": "startup"})
	status = StatusStore()
	stop_event = Event()
	pause_event = Event()
	manual_scan_event = Event()
	notifier_thread = _start_notifier(
		config, status, stop_event, pause_event, manual_scan_event
	)

	edit_process: subprocess.Popen[str] | None = None
	status_process: subprocess.Popen[str] | None = None

	icon = pystray.Icon(
		"sentineltray",
		_build_tray_image(),
		"SentinelTray (Running)",
	)

	def on_open(_: pystray.Icon, __: pystray.MenuItem) -> None:
		nonlocal edit_process
		if edit_process is not None and edit_process.poll() is None:
			return
		try:
			data_dir = get_user_data_dir()
			config_path = data_dir / "config.local.yaml"
			encrypted_path = get_encrypted_config_path(config_path)
			temp_path = data_dir / "config.local.yaml.edit"

			if encrypted_path.exists():
				payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
				plaintext = decrypt_config_payload(payload, config_path=config_path)
				temp_path.write_text(plaintext, encoding="utf-8")
			elif config_path.exists():
				temp_path.write_text(
					config_path.read_text(encoding="utf-8"),
					encoding="utf-8",
				)
			else:
				LOGGER.warning("Config file not found to edit")
				return

			edit_process = subprocess.Popen(["notepad.exe", str(temp_path)])
		except Exception as exc:
			LOGGER.warning("Failed to open config editor: %s", exc)

	def finalize_config_edit() -> None:
		nonlocal edit_process
		if edit_process is None:
			return
		if edit_process.poll() is None:
			return
		edit_process = None
		try:
			data_dir = get_user_data_dir()
			config_path = data_dir / "config.local.yaml"
			encrypted_path = get_encrypted_config_path(config_path)
			temp_path = data_dir / "config.local.yaml.edit"
			if not temp_path.exists():
				return
			try:
				load_config(str(temp_path))
			except Exception as exc:
				LOGGER.warning("Config validation failed after edit: %s", exc)
				temp_path.unlink(missing_ok=True)
				return

			plaintext = temp_path.read_text(encoding="utf-8")
			encoded = encrypt_config_text(plaintext, config_path=config_path)
			encrypted_path.write_text(encoded, encoding="utf-8")
			if config_path.exists():
				config_path.unlink()
			temp_path.unlink(missing_ok=True)
		except Exception as exc:
			LOGGER.warning("Failed to finalize config edit: %s", exc)

	def on_status(_: pystray.Icon, __: pystray.MenuItem) -> None:
		nonlocal status_process
		if status_process is not None and status_process.poll() is None:
			return
		try:
			creationflags = 0
			if os.name == "nt":
				creationflags = subprocess.CREATE_NEW_CONSOLE
			status_process = subprocess.Popen(
				[sys.executable, "-m", "sentineltray.status_cli"],
				creationflags=creationflags,
			)
		except Exception as exc:
			LOGGER.warning("Failed to open status console: %s", exc)

	def on_exit(_: pystray.Icon, __: pystray.MenuItem) -> None:
		LOGGER.info("Exit requested", extra={"category": "startup"})
		stop_event.set()
		icon.stop()

	icon.menu = pystray.Menu(
		pystray.MenuItem("Config", on_open),
		pystray.MenuItem("Status (CLI)", on_status),
		pystray.MenuItem("Exit", on_exit),
	)
	try:
		icon.run_detached()
		while not stop_event.is_set():
			stop_event.wait(0.5)
			snapshot = status.snapshot()
			label = "SentinelTray"
			if snapshot.paused:
				label = "SentinelTray (Paused)"
			elif snapshot.last_error:
				label = "SentinelTray (Error)"
			elif snapshot.running:
				label = "SentinelTray (Running)"
			if icon.title != label:
				icon.title = label
			finalize_config_edit()
	except Exception as exc:
		LOGGER.error("Tray icon failed: %s", exc)
	finally:
		stop_event.set()
		try:
			icon.stop()
		except Exception:
			pass
		notifier_thread.join(timeout=5)
