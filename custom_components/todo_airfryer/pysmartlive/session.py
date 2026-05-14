"""Lower LAN session layer: identity, probe, beacon decode."""
from __future__ import annotations

import socket
import struct
from dataclasses import dataclass

from .protocol import encode_frame

DEFAULT_ARCH_IDENTITY = "IOT-3951-XWPSS"
DB0_FIXTURE = 0x69FF0A9F


@dataclass(frozen=True)
class LowerArchIdentity:
    prefix8: bytes
    number: int
    suffix8: bytes

    @property
    def packed_key20(self) -> bytes:
        return (
            self.prefix8.ljust(8, b"\x00")
            + self.suffix8.ljust(8, b"\x00")
            + (self.number & 0xFFFFFFFF).to_bytes(4, "big")
        )

    @property
    def beacon_payload32_request(self) -> bytes:
        return self.packed_key20 + b"\x00" * 12


@dataclass(frozen=True)
class SessionBeacon71:
    identity: LowerArchIdentity
    fryer_port: int


def parse_arch_identity(src: str) -> LowerArchIdentity:
    parts = src.split("-")
    if len(parts) != 3:
        raise ValueError(f"identity must be A-N-B form, got {src!r}")
    prefix, num_s, suffix = parts
    return LowerArchIdentity(prefix.encode()[:8], int(num_s), suffix.encode()[:8])


def build_session_probe_packet(identity: str = DEFAULT_ARCH_IDENTITY, *, nonce: bytes | None = None) -> bytes:
    payload = parse_arch_identity(identity).beacon_payload32_request
    return encode_frame(payload, state=0x70, nonce=nonce, checksum_algo="lan")


def parse_session_beacon(payload: bytes) -> SessionBeacon71:
    if len(payload) != 32:
        raise ValueError(f"state=0x71 beacon payload must be 32 bytes, got {len(payload)}")
    identity = LowerArchIdentity(
        payload[0:8].rstrip(b"\x00"),
        int.from_bytes(payload[16:20], "big"),
        payload[8:16].rstrip(b"\x00"),
    )
    return SessionBeacon71(identity=identity, fryer_port=int.from_bytes(payload[24:26], "big"))


@dataclass
class SmartLiveLanIdentity:
    """Identity carried in the 64-byte LAN IOT/XWPSS prefix."""

    client_ip: str
    client_port: int
    lower_counter: int = 0x4B


def build_iot_xwpss_prefix(identity: SmartLiveLanIdentity, inner_len: int = 0x60) -> bytes:
    b = bytearray(bytes.fromhex(
        "494f540000000000"
        "5857505353000000"
        "00000f6f00000000"
        "ff6a509769ff0a9f"
        "000000000000000000000000"
        "c0a8006a"
        "69ff0a9f"
        "0000004c0060509700000000"
    ))
    b[44:48] = socket.inet_aton(identity.client_ip)
    port_be = struct.pack(">H", identity.client_port)
    b[26:28] = port_be
    b[55] = identity.lower_counter & 0xFF
    b[57] = inner_len & 0xFF
    b[58:60] = port_be
    db0 = DB0_FIXTURE.to_bytes(4, "big")
    b[28:32] = db0
    b[48:52] = db0
    return bytes(b)


def lan_payload(inner: bytes, identity: SmartLiveLanIdentity) -> bytes:
    return build_iot_xwpss_prefix(identity, inner_len=len(inner)) + inner
