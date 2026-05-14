"""Inner-frame composer for SmartLive cooker commands.

Builds the plaintext 5a41... inner frames that get wrapped in the SDK transport.
Header layout is type-specific; bytes 4 and beyond carry per-type markers
recovered from the iOS app's outgoing frames.
"""
from __future__ import annotations

PAD = b"\x00" * 64


def _login_hdr(password: bytes) -> bytes:
    """24-byte login header: 5a41 0101 0000 0a75 <pw5> 00 38 00 74 + 7 nulls.

    Captured SmartLiveDevice Login from SMART_d139.
    """
    pw = password[:5].ljust(5, b"\x00")
    return (
        bytes([0x5A, 0x41, 0x01, 0x01, 0x00, 0x00, 0x0A, 0x75])
        + pw
        + bytes([0x00, 0x38, 0x00, 0x74])
        + b"\x00" * 7
    )


def _control_hdr(password: bytes) -> bytes:
    """24-byte 5a4106 header: 5a41 0601 0800 0a75 <pw5> + 11 nulls."""
    pw = password[:5].ljust(5, b"\x00")
    return bytes([0x5A, 0x41, 0x06, 0x01, 0x08, 0x00, 0x0A, 0x75]) + pw + b"\x00" * 11


def _status_get_hdr(password: bytes) -> bytes:
    """24-byte 5a410d header: 5a41 0d01 0000 0a75 <pw5> + 11 nulls."""
    pw = password[:5].ljust(5, b"\x00")
    return bytes([0x5A, 0x41, 0x0D, 0x01, 0x00, 0x00, 0x0A, 0x75]) + pw + b"\x00" * 11


def rec(code: int, value: int = 0) -> bytes:
    """8-byte 0x71 ... 0x5A appliance record."""
    return bytes([0x71, code & 0xFF, value & 0xFF, 0, 0, 0, 0, 0x5A])


def inner_06(records: list[bytes], seq: int = 0, password: bytes = b"fryme") -> bytes:
    """Build a 5a4106 control frame containing up to eight 8-byte records."""
    body = b"".join(records)
    if len(body) > 64:
        raise ValueError("record body too long for 88-byte inner frame")
    body = body + b"\x00" * (64 - len(body))
    tail = b"\x00" * 6 + bytes([seq & 0xFF, 0])
    return _control_hdr(password) + body + tail


def inner_01_login(seq: int = 0, password: bytes = b"fryme") -> bytes:
    """Build a 5a4101 login frame."""
    return _login_hdr(password) + PAD + (b"\x00" * 6 + bytes([seq & 0xFF, 0]))


def inner_0d(seq: int = 0, password: bytes = b"fryme") -> bytes:
    """Build a 5a410d status-get frame."""
    return _status_get_hdr(password) + PAD + (b"\x00" * 6 + bytes([seq & 0xFF, 0]))
