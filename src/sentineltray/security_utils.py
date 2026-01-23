from __future__ import annotations

import base64
import ctypes
from dataclasses import dataclass


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.c_void_p)]


@dataclass(frozen=True)
class EncryptedPayload:
    method: str
    data: bytes


_DPPAPI_ENTROPY = b"sentineltray-config-v1"


class DataProtectionError(RuntimeError):
    """Raised when encryption or decryption fails."""


def _blob_from_bytes(data: bytes) -> tuple[_DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.c_void_p))
    return blob, buffer


def _bytes_from_blob(blob: _DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData <= 0:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _crypt_protect(data: bytes, entropy: bytes | None) -> bytes:
    if not data:
        raise DataProtectionError("No data to encrypt")
    if not hasattr(ctypes, "windll"):
        raise DataProtectionError("DPAPI is only available on Windows")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.POINTER(_DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = ctypes.c_bool
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    input_blob, _buffer = _blob_from_bytes(data)
    entropy_blob = None
    if entropy:
        entropy_blob, _entropy_buffer = _blob_from_bytes(entropy)
    output_blob = _DATA_BLOB()

    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        ctypes.byref(entropy_blob) if entropy_blob else None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise DataProtectionError("CryptProtectData failed")

    try:
        encrypted = _bytes_from_blob(output_blob)
        if not encrypted:
            raise DataProtectionError("CryptProtectData returned empty data")
        return encrypted
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)


def _crypt_unprotect(data: bytes, entropy: bytes | None) -> bytes:
    if not data:
        raise DataProtectionError("No data to decrypt")
    if not hasattr(ctypes, "windll"):
        raise DataProtectionError("DPAPI is only available on Windows")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.POINTER(_DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.POINTER(_DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.c_bool
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    input_blob, _buffer = _blob_from_bytes(data)
    entropy_blob = None
    if entropy:
        entropy_blob, _entropy_buffer = _blob_from_bytes(entropy)
    output_blob = _DATA_BLOB()

    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        ctypes.byref(entropy_blob) if entropy_blob else None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise DataProtectionError("CryptUnprotectData failed")

    try:
        decrypted = _bytes_from_blob(output_blob)
        if not decrypted:
            raise DataProtectionError("CryptUnprotectData returned empty data")
        return decrypted
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)


def encrypt_text_dpapi(text: str) -> EncryptedPayload:
    raw = text.encode("utf-8")
    encrypted = _crypt_protect(raw, _DPPAPI_ENTROPY)
    return EncryptedPayload(method="dpapi", data=encrypted)


def decrypt_text_dpapi(payload: EncryptedPayload) -> str:
    if payload.method != "dpapi":
        raise DataProtectionError(f"Unsupported encryption method: {payload.method}")
    decrypted = _crypt_unprotect(payload.data, _DPPAPI_ENTROPY)
    return decrypted.decode("utf-8")


def serialize_payload(payload: EncryptedPayload) -> str:
    encoded = base64.b64encode(payload.data).decode("ascii")
    return f"dpapi:{encoded}"


def parse_payload(text: str) -> EncryptedPayload:
    text = text.strip()
    if not text:
        raise DataProtectionError("Encrypted payload is empty")
    if not text.startswith("dpapi:"):
        raise DataProtectionError("Unsupported encrypted payload format")
    encoded = text.split(":", 1)[1]
    return EncryptedPayload(method="dpapi", data=base64.b64decode(encoded))
