from __future__ import annotations

import argparse
import cmd
import subprocess
from pathlib import Path

from .config import (
    get_encrypted_config_path,
    get_user_data_dir,
    load_config,
)
from .security_utils import decrypt_text_dpapi, encrypt_text_dpapi, parse_payload, serialize_payload


class SentinelTrayShell(cmd.Cmd):
    intro = (
        "SentinelTray CLI\n"
        "Commands:\n"
        "  edit_config  Open the config editor (auto-encrypt on save)\n"
        "  help         Show this message\n"
        "  quit         Exit the CLI\n"
    )
    prompt = "sentineltray> "

    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self._config_path = config_path

    def do_quit(self, _arg: str) -> bool:
        """Exit this CLI."""
        return True

    def do_EOF(self, _arg: str) -> bool:
        self.stdout.write("\n")
        return True

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


def _resolve_config_path() -> Path:
    data_dir = get_user_data_dir()
    return data_dir / "config.local.yaml"


def _cli_main() -> int:
    parser = argparse.ArgumentParser(description="SentinelTray CLI")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["edit_config"],
        help="Run a single command and exit.",
    )
    args = parser.parse_args()

    config_path = _resolve_config_path()

    if args.command is None:
        SentinelTrayShell(config_path).cmdloop()
        return 0

    if args.command == "edit_config":
        SentinelTrayShell(config_path).do_edit_config("")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
