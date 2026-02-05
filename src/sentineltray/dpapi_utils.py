from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _bytes_to_blob(data: bytes) -> DATA_BLOB:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def encrypt_bytes(data: bytes) -> bytes:
    if not data:
        return b""
    in_blob = _bytes_to_blob(data)
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("CryptProtectData failed")
    try:
        return _blob_to_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def decrypt_bytes(data: bytes) -> bytes:
    if not data:
        return b""
    in_blob = _bytes_to_blob(data)
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("CryptUnprotectData failed")
    try:
        return _blob_to_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def save_secret(path: Path, value: str) -> None:
    data = encrypt_bytes(value.encode("utf-8"))
    encoded = base64.b64encode(data).decode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def load_secret(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    data = base64.b64decode(raw)
    decrypted = decrypt_bytes(data)
    return decrypted.decode("utf-8")
