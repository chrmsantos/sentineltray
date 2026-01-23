from __future__ import annotations

import argparse
import cmd
import json
import subprocess
from pathlib import Path

from .cli_control import write_command
from .config import (
    get_encrypted_config_path,
    get_user_data_dir,
    load_config,
    load_config_secure,
    encrypt_config_file,
    decrypt_config_file,
)
from .security_utils import decrypt_text_dpapi, encrypt_text_dpapi, parse_payload, serialize_payload
from .status import format_status


class SentinelTrayShell(cmd.Cmd):
    intro = "SentinelTray CLI. Type 'help' for commands."
    prompt = "sentineltray> "

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self._config_path = config_path

    def do_status(self, _arg: str) -> None:
        """Show last exported status."""
        try:
            config = load_config_secure(str(self._config_path))
        except Exception as exc:
            self.stdout.write(f"Failed to load config: {exc}\n")
            return

        status_path = Path(config.status_export_file)
        if not status_path.is_absolute():
            status_path = get_user_data_dir() / status_path

        if not status_path.exists():
            self.stdout.write("Status export not found.\n")
            return

        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.stdout.write(f"Failed to read status export: {exc}\n")
            return

        if not isinstance(data, dict):
            self.stdout.write("Status export format is invalid.\n")
            return

        try:
            text = format_status(
                _snapshot_from_json(data),
                window_title_regex=config.window_title_regex,
                phrase_regex=config.phrase_regex,
                poll_interval_seconds=config.poll_interval_seconds,
            )
        except Exception as exc:
            self.stdout.write(f"Failed to format status: {exc}\n")
            return

        self.stdout.write(text + "\n")

    def do_pause(self, _arg: str) -> None:
        """Pause scanning."""
        write_command("pause")
        self.stdout.write("Pause requested.\n")

    def do_resume(self, _arg: str) -> None:
        """Resume scanning."""
        write_command("resume")
        self.stdout.write("Resume requested.\n")

    def do_scan(self, _arg: str) -> None:
        """Request an immediate scan."""
        write_command("scan")
        self.stdout.write("Manual scan requested.\n")

    def do_exit(self, _arg: str) -> bool:
        """Stop SentinelTray and exit this CLI."""
        write_command("exit")
        self.stdout.write("Exit requested.\n")
        return True

    def do_quit(self, _arg: str) -> bool:
        """Exit this CLI."""
        return True

    def do_EOF(self, _arg: str) -> bool:
        self.stdout.write("\n")
        return True

    def do_encrypt_config(self, arg: str) -> None:
        """Encrypt config.local.yaml (DPAPI). Use 'encrypt_config --keep-plain' to keep plaintext."""
        keep_plain = "--keep-plain" in arg
        try:
            encrypted_path = encrypt_config_file(str(self._config_path), remove_plain=not keep_plain)
        except Exception as exc:
            self.stdout.write(f"Failed to encrypt config: {exc}\n")
            return
        self.stdout.write(f"Encrypted config written to {encrypted_path}\n")

    def do_decrypt_config(self, _arg: str) -> None:
        """Decrypt config.local.yaml.enc back to plaintext."""
        try:
            plain_path = decrypt_config_file(str(self._config_path))
        except Exception as exc:
            self.stdout.write(f"Failed to decrypt config: {exc}\n")
            return
        self.stdout.write(f"Decrypted config written to {plain_path}\n")

    def do_edit_config(self, _arg: str) -> None:
        """Open the config in a local editor and re-encrypt it on save."""
        data_dir = get_user_data_dir()
        temp_path = data_dir / "config.local.yaml.edit"
        encrypted_path = get_encrypted_config_path(self._config_path)

        try:
            if encrypted_path.exists():
                payload = parse_payload(encrypted_path.read_text(encoding="utf-8"))
                plaintext = decrypt_text_dpapi(payload)
                temp_path.write_text(plaintext, encoding="utf-8")
            elif self._config_path.exists():
                temp_path.write_text(
                    self._config_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            else:
                self.stdout.write("Config file not found.\n")
                return
        except Exception as exc:
            self.stdout.write(f"Failed to prepare config for editing: {exc}\n")
            return

        try:
            subprocess.run(["notepad.exe", str(temp_path)], check=False)
        except Exception as exc:
            self.stdout.write(f"Failed to open editor: {exc}\n")
            return

        try:
            load_config(str(temp_path))
        except Exception as exc:
            self.stdout.write("Config validation failed. Changes not saved.\n")
            self.stdout.write(f"Details: {exc}\n")
            self.stdout.write(f"Fix the file at: {temp_path}\n")
            return

        try:
            plaintext = temp_path.read_text(encoding="utf-8")
            payload = encrypt_text_dpapi(plaintext)
            encrypted_path.write_text(serialize_payload(payload), encoding="utf-8")
            if self._config_path.exists():
                self._config_path.unlink()
            temp_path.unlink(missing_ok=True)
        except Exception as exc:
            self.stdout.write(f"Failed to encrypt config: {exc}\n")
            self.stdout.write(f"Temporary file kept at: {temp_path}\n")
            return

        self.stdout.write("Config updated and encrypted.\n")


def _snapshot_from_json(data: dict[str, object]):
    from .status import StatusSnapshot

    return StatusSnapshot(
        running=bool(data.get("running")),
        paused=bool(data.get("paused")),
        last_scan=str(data.get("last_scan", "")),
        last_match=str(data.get("last_match", "")),
        last_match_at=str(data.get("last_match_at", "")),
        last_send=str(data.get("last_send", "")),
        last_error=str(data.get("last_error", "")),
        last_healthcheck=str(data.get("last_healthcheck", "")),
        uptime_seconds=int(data.get("uptime_seconds", 0) or 0),
        error_count=int(data.get("error_count", 0) or 0),
    )


def _resolve_config_path() -> Path:
    data_dir = get_user_data_dir()
    return data_dir / "config.local.yaml"


def _cli_main() -> int:
    parser = argparse.ArgumentParser(description="SentinelTray CLI")
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "status",
            "pause",
            "resume",
            "scan",
            "exit",
            "encrypt",
            "decrypt",
            "edit",
        ],
        help="Run a single command and exit.",
    )
    parser.add_argument(
        "--keep-plain",
        action="store_true",
        help="Keep the plaintext config when encrypting.",
    )
    args = parser.parse_args()

    config_path = _resolve_config_path()

    if args.command is None:
        SentinelTrayShell(config_path).cmdloop()
        return 0

    if args.command == "status":
        SentinelTrayShell(config_path).do_status("")
        return 0
    if args.command == "pause":
        write_command("pause")
        return 0
    if args.command == "resume":
        write_command("resume")
        return 0
    if args.command == "scan":
        write_command("scan")
        return 0
    if args.command == "exit":
        write_command("exit")
        return 0
    if args.command == "encrypt":
        encrypt_config_file(str(config_path), remove_plain=not args.keep_plain)
        return 0
    if args.command == "decrypt":
        decrypt_config_file(str(config_path))
        return 0
    if args.command == "edit":
        SentinelTrayShell(config_path).do_edit_config("")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
